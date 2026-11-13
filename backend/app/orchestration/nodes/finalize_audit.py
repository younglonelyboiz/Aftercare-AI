"""
Nút hoàn tất phản hồi, ghi nhận nhật ký kiểm toán bất biến (Append-only Audit)
và thu thập chỉ số độ trễ P50/P95 theo từng nút — [W07-T5.3, T5.5].
"""
import hashlib
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.guardrails.pii_redactor import default_pii_redactor
from backend.app.guardrails.templates_vi import SAFE_FALLBACK_MESSAGE
from backend.app.models.audit import AgentActionLog, AuditLog
from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState

logger = logging.getLogger("OrchestrationAudit")

DEFAULT_METRICS_PATH = (
    Path(__file__).resolve().parents[4] / "Evidence" / "W07" / "metrics.json"
)

_LAYER_TO_NODE_MAP = {
    "L0_CONTEXT": "load_context",
    "L0_SANITIZE": "sanitize_input",
    "L1_SAFETY": "safety_triage",
    "L2_POLICY": "policy_guard",
    "L3_EVIDENCE": "retrieve_evidence",
    "L4_GENERATION": "generate_answer",
    "L5_OUTPUT": "output_guard",
    "L6_ESCALATION": "escalate",
    "L7_AUDIT": "finalize",
}


def _percentile(sorted_vals: List[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(sorted_vals[low])
    weight = rank - low
    return float(sorted_vals[low] * (1.0 - weight) + sorted_vals[high] * weight)


class OrchestrationMetricsCollector:
    """Bộ thu thập chỉ số quan sát (Observability Metrics) và tính phân vị độ trễ P50/P95 theo từng nút."""

    def __init__(self):
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.total_traces: int = 0
            self.node_latencies: Dict[str, List[int]] = defaultdict(list)
            self.end_to_end_latencies_by_risk: Dict[str, List[int]] = defaultdict(list)
            self.guard_block_total: Dict[str, int] = defaultdict(int)
            self.guard_rewrite_total: Dict[str, int] = defaultdict(int)
            self.risk_level_total: Dict[str, int] = defaultdict(int)
            self.llm_fallback_total: int = 0
            self.evidence_gate_reject_total: int = 0

    def record_turn(self, state: AftercareState) -> None:
        latency_map = state.get("latency_ms") or {}
        events = state.get("guard_events") or []
        risk = str(state.get("risk_level") or "NORMAL")

        with self._lock:
            self.total_traces += 1
            self.risk_level_total[risk] += 1

            total_ms = 0
            for node_name, ms in latency_map.items():
                val = int(ms or 0)
                self.node_latencies[node_name].append(val)
                total_ms += val
            self.end_to_end_latencies_by_risk[risk].append(total_ms)

            if state.get("degraded"):
                self.llm_fallback_total += 1
            if state.get("evidence_ok") is False:
                self.evidence_gate_reject_total += 1

            for ev in events:
                decision = str(ev.get("decision") or "")
                rule_id = str(ev.get("rule_id") or "UNKNOWN")
                if decision == "BLOCKED":
                    self.guard_block_total[rule_id] += 1
                elif decision == "REWRITTEN":
                    self.guard_rewrite_total[rule_id] += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            node_stats: Dict[str, Dict[str, Any]] = {}
            for node_name, samples in sorted(self.node_latencies.items()):
                s = sorted(samples)
                node_stats[node_name] = {
                    "count": len(s),
                    "p50_ms": round(_percentile(s, 50), 2),
                    "p95_ms": round(_percentile(s, 95), 2),
                    "mean_ms": round(sum(s) / len(s), 2) if s else 0.0,
                    "max_ms": max(s) if s else 0,
                }

            risk_latency_stats: Dict[str, Dict[str, Any]] = {}
            for risk_name, samples in sorted(
                self.end_to_end_latencies_by_risk.items()
            ):
                s = sorted(samples)
                risk_latency_stats[risk_name] = {
                    "count": len(s),
                    "p50_ms": round(_percentile(s, 50), 2),
                    "p95_ms": round(_percentile(s, 95), 2),
                    "mean_ms": round(sum(s) / len(s), 2) if s else 0.0,
                }

            return {
                "generated_at": datetime.utcnow().isoformat(),
                "total_traces": self.total_traces,
                "risk_level_total": dict(self.risk_level_total),
                "llm_fallback_total": self.llm_fallback_total,
                "evidence_gate_reject_total": self.evidence_gate_reject_total,
                "guard_block_total": dict(self.guard_block_total),
                "guard_rewrite_total": dict(self.guard_rewrite_total),
                "node_latency_ms": node_stats,
                "end_to_end_latency_by_risk_ms": risk_latency_stats,
            }

    def export_json(self, path: Optional[Path] = None) -> Path:
        target = path or DEFAULT_METRICS_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target


metrics_collector = OrchestrationMetricsCollector()

# Bộ nhớ đệm 500 trace gần nhất phục vụ tra cứu nhanh và kiểm thử độc lập
_recent_traces_lock = Lock()
_recent_traces: Dict[str, Dict[str, Any]] = {}
_audit_session_factory: Optional[Callable[[], Session]] = None


def set_audit_session_factory(factory: Optional[Callable[[], Session]]) -> None:
    """Cấu hình factory tạo Session cơ sở dữ liệu cho việc ghi nhật ký kiểm toán."""
    global _audit_session_factory
    _audit_session_factory = factory
    from backend.app.services.audit_service import set_system_audit_session_factory

    set_system_audit_session_factory(factory)


def get_cached_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    with _recent_traces_lock:
        return _recent_traces.get(trace_id)


def persist_audit_trace(
    state: AftercareState,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Lưu 1 bản ghi `AgentActionLog` và N bản ghi `AuditLog` (append-only, đã che PII) cho lượt chat."""
    trace_id = str(state.get("trace_id") or "")
    session_id = state.get("session_id")
    patient_id = str(state.get("patient_id") or "UNKNOWN")
    channel = str(state.get("channel") or "CHAT")
    raw_msg = str(state.get("raw_message") or "")
    profile = state.get("profile") or {}

    msg_sha256 = hashlib.sha256(raw_msg.encode("utf-8")).hexdigest()
    redacted_msg = default_pii_redactor.redact_text(raw_msg, profile=profile)

    latency_map = dict(state.get("latency_ms") or {})
    total_latency_ms = sum(int(v or 0) for v in latency_map.values())
    guard_events = list(state.get("guard_events") or [])

    action_dict = {
        "trace_id": trace_id,
        "session_id": session_id,
        "patient_id": patient_id,
        "channel": channel,
        "message_sha256": msg_sha256,
        "redacted_message": redacted_msg,
        "risk_level": str(state.get("risk_level") or "NORMAL"),
        "policy_decision": state.get("policy_decision"),
        "policy_rule_id": state.get("policy_rule_id"),
        "evidence_ok": bool(state.get("evidence_ok", True)),
        "output_guard_decision": state.get("output_guard_decision"),
        "degraded": bool(state.get("degraded", False)),
        "escalation_ticket_id": state.get("ticket_id"),
        "latency_ms": latency_map,
        "total_latency_ms": total_latency_ms,
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }

    event_dicts: List[Dict[str, Any]] = []
    for idx, ev in enumerate(guard_events, start=1):
        layer = str(ev.get("layer") or "UNKNOWN")
        node_name = _LAYER_TO_NODE_MAP.get(layer, layer.lower())
        node_lat = int(latency_map.get(node_name, 0))
        redacted_detail = default_pii_redactor.redact_text(
            str(ev.get("detail") or ""), profile=profile
        )
        event_dicts.append(
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "patient_id": patient_id,
                "sequence": idx,
                "node": node_name,
                "layer": layer,
                "rule_id": str(ev.get("rule_id") or "UNKNOWN"),
                "decision": str(ev.get("decision") or "PASSED"),
                "detail": redacted_detail,
                "latency_ms": node_lat,
                "created_at": str(
                    ev.get("timestamp")
                    or datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                ),
            }
        )

    trace_bundle = {"action": action_dict, "events": event_dicts}
    if trace_id:
        with _recent_traces_lock:
            if len(_recent_traces) >= 500:
                oldest_key = next(iter(_recent_traces))
                _recent_traces.pop(oldest_key, None)
            _recent_traces[trace_id] = trace_bundle

    own_session = False
    session = db
    if session is None and _audit_session_factory is not None:
        try:
            session = _audit_session_factory()
            own_session = session is not None
        except Exception:
            session = None

    if session is not None and trace_id:
        try:
            action_row = AgentActionLog(
                trace_id=trace_id,
                session_id=session_id,
                patient_id=patient_id,
                channel=channel,
                message_sha256=msg_sha256,
                redacted_message=redacted_msg,
                risk_level=action_dict["risk_level"],
                policy_decision=action_dict["policy_decision"],
                policy_rule_id=action_dict["policy_rule_id"],
                evidence_ok=action_dict["evidence_ok"],
                output_guard_decision=action_dict["output_guard_decision"],
                degraded=action_dict["degraded"],
                escalation_ticket_id=action_dict["escalation_ticket_id"],
                latency_ms=latency_map,
                total_latency_ms=total_latency_ms,
            )
            session.add(action_row)
            for item in event_dicts:
                session.add(
                    AuditLog(
                        trace_id=item["trace_id"],
                        session_id=item["session_id"],
                        patient_id=item["patient_id"],
                        sequence=item["sequence"],
                        node=item["node"],
                        layer=item["layer"],
                        rule_id=item["rule_id"],
                        decision=item["decision"],
                        detail=item["detail"],
                        latency_ms=item["latency_ms"],
                    )
                )
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
            logger.debug(
                "Bỏ qua ghi DB cho trace %s (bảng kiểm toán chưa khởi tạo hoặc kết nối tạm gián đoạn).",
                trace_id,
            )
        finally:
            if own_session:
                try:
                    session.close()
                except Exception:
                    pass

    from backend.app.services.audit_service import default_audit_service

    default_audit_service.record_event(
        category="AGENT",
        action_code="AGENT.GRAPH_TURN_COMPLETED",
        actor_id="aftercare_graph",
        actor_role="agent",
        patient_id=patient_id,
        session_id=session_id,
        trace_id=trace_id,
        resource_type="ChatTurn",
        resource_id=trace_id,
        severity=(
            "CRITICAL"
            if action_dict["risk_level"] == "RED_ZONE"
            else ("HIGH" if action_dict["risk_level"] == "YELLOW_ZONE" else "INFO")
        ),
        after_state={
            "risk_level": action_dict["risk_level"],
            "policy_decision": action_dict["policy_decision"],
            "policy_rule_id": action_dict["policy_rule_id"],
            "evidence_ok": action_dict["evidence_ok"],
            "output_guard_decision": action_dict["output_guard_decision"],
            "degraded": action_dict["degraded"],
            "total_latency_ms": total_latency_ms,
        },
        profile=profile,
    )

    return trace_bundle


def make_finalize_node():
    """Tạo nút `finalize`: bảo đảm luôn có chuỗi phản hồi hợp lệ trước khi kết thúc."""

    @safe_node("finalize", layer="L7_AUDIT")
    def finalize_node(state: AftercareState) -> Dict[str, Any]:
        text = (state.get("response_text") or "").strip()
        if not text:
            return {
                "response_text": SAFE_FALLBACK_MESSAGE,
                "citations": [],
                "degraded": True,
            }
        return {}

    return finalize_node


def make_audit_node():
    """Tạo nút `audit`: ghi nhật ký hành động append-only (đã ẩn danh PII) và thu thập độ trễ P50/P95."""

    @safe_node("audit", layer="L7_AUDIT")
    def audit_node(state: AftercareState) -> Dict[str, Any]:
        metrics_collector.record_turn(state)
        persist_audit_trace(state)
        logger.info(
            "trace_id=%s patient_id=%s risk=%s degraded=%s events=%d latency_ms=%s",
            state.get("trace_id"),
            state.get("patient_id"),
            state.get("risk_level"),
            state.get("degraded"),
            len(state.get("guard_events") or []),
            state.get("latency_ms"),
        )
        return {}

    return audit_node


__all__ = [
    "DEFAULT_METRICS_PATH",
    "OrchestrationMetricsCollector",
    "get_cached_trace",
    "make_audit_node",
    "make_finalize_node",
    "metrics_collector",
    "persist_audit_trace",
    "set_audit_session_factory",
]
