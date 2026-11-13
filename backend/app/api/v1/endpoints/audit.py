"""
Endpoint chỉ đọc (Read-only Audit API) dành cho Quản trị viên để tra cứu dấu vết điều phối
và chỉ số quan sát độ trễ P50/P95 — [W07-T5.4, T5.5].

Tuân thủ nguyên tắc kiểm toán bất biến (Append-only):
- Chỉ cung cấp các phương thức đọc (`GET`), tuyệt đối không có endpoint `PUT`, `PATCH` hoặc `DELETE`.
- Yêu cầu quyền `admin` (`Depends(admin_user)`).
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import admin_user
from backend.app.models.audit import AgentActionLog, AuditLog
from backend.app.orchestration.nodes.finalize_audit import (
    get_cached_trace,
    metrics_collector,
)

router = APIRouter(dependencies=[Depends(admin_user)])


def _action_row_to_dict(row: AgentActionLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "trace_id": row.trace_id,
        "session_id": row.session_id,
        "patient_id": row.patient_id,
        "channel": row.channel,
        "message_sha256": row.message_sha256,
        "redacted_message": row.redacted_message,
        "risk_level": row.risk_level,
        "policy_decision": row.policy_decision,
        "policy_rule_id": row.policy_rule_id,
        "evidence_ok": row.evidence_ok,
        "output_guard_decision": row.output_guard_decision,
        "degraded": row.degraded,
        "escalation_ticket_id": row.escalation_ticket_id,
        "latency_ms": row.latency_ms or {},
        "total_latency_ms": row.total_latency_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _event_row_to_dict(row: AuditLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "trace_id": row.trace_id,
        "session_id": row.session_id,
        "patient_id": row.patient_id,
        "sequence": row.sequence,
        "node": row.node,
        "layer": row.layer,
        "rule_id": row.rule_id,
        "decision": row.decision,
        "detail": row.detail,
        "latency_ms": row.latency_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/traces/{trace_id}")
def get_audit_trace(trace_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Xem toàn bộ đường đi qua đồ thị điều phối và các sự kiện hàng rào an toàn của một lượt hội thoại."""
    try:
        action_row = db.scalar(
            select(AgentActionLog).where(AgentActionLog.trace_id == trace_id)
        )
        if action_row is not None:
            event_rows: List[AuditLog] = list(
                db.scalars(
                    select(AuditLog)
                    .where(AuditLog.trace_id == trace_id)
                    .order_by(AuditLog.sequence)
                ).all()
            )
            return {
                "trace_id": trace_id,
                "action": _action_row_to_dict(action_row),
                "events": [_event_row_to_dict(r) for r in event_rows],
            }
    except Exception:
        pass

    cached = get_cached_trace(trace_id)
    if cached is not None:
        return {
            "trace_id": trace_id,
            "action": cached["action"],
            "events": cached["events"],
        }

    raise HTTPException(
        status_code=404,
        detail=f"Không tìm thấy dấu vết kiểm toán cho mã trace_id: {trace_id}",
    )


@router.get("/metrics")
def get_orchestration_metrics() -> Dict[str, Any]:
    """Trả về thống kê độ trễ P50/P95 theo từng nút và bộ đếm sự kiện hàng rào an toàn."""
    return metrics_collector.snapshot()

