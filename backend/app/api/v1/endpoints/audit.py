"""
Endpoint chỉ đọc (Read-only Audit API) dành cho Quản trị viên để tra cứu dấu vết điều phối,
danh sách sự kiện toàn hệ thống, kiểm định chuỗi băm chống giả mạo và chỉ số độ trễ P50/P95 — [W07-T5.4, T5.5, AUD-5].

Tuân thủ nguyên tắc kiểm toán bất biến (Append-only):
- Chỉ cung cấp các phương thức đọc (`GET`), tuyệt đối không có endpoint `PUT`, `PATCH` hoặc `DELETE`.
- Yêu cầu quyền `admin` (`Depends(admin_user)`).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import admin_user
from backend.app.models.audit import AgentActionLog, AuditLog, SystemAuditLog
from backend.app.orchestration.nodes.finalize_audit import (
    get_cached_trace,
    metrics_collector,
)
from backend.app.services.audit_service import default_audit_service

router = APIRouter(dependencies=[Depends(admin_user)])


def _to_utc_iso(dt: Optional[Any]) -> Optional[str]:
    if not dt:
        return None
    raw = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
    if raw.endswith("Z") or "+" in raw[10:]:
        return raw
    return f"{raw}Z"


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
        "created_at": _to_utc_iso(row.created_at),
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
        "created_at": _to_utc_iso(row.created_at),
    }


def _system_row_to_dict(row: SystemAuditLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "chain_seq": row.chain_seq,
        "trace_id": row.trace_id,
        "session_id": row.session_id,
        "actor_id": row.actor_id,
        "actor_role": row.actor_role,
        "patient_id": row.patient_id,
        "category": row.category,
        "action_code": row.action_code,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "http_method": row.http_method,
        "http_path": row.http_path,
        "status_code": row.status_code,
        "severity": row.severity,
        "before_state": row.before_state or {},
        "after_state": row.after_state or {},
        "metadata_json": row.metadata_json or {},
        "client_ip_hash": row.client_ip_hash,
        "prev_hash": row.prev_hash,
        "record_hash": row.record_hash,
        "created_at": _to_utc_iso(row.created_at),
    }


@router.get("/traces/{trace_id}")
def get_audit_trace(trace_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Xem toàn bộ đường đi qua đồ thị điều phối, các sự kiện hàng rào an toàn và sự kiện hệ thống của một mã `trace_id`."""
    system_events: List[Dict[str, Any]] = []
    try:
        sys_rows = db.scalars(
            select(SystemAuditLog)
            .where(SystemAuditLog.trace_id == trace_id)
            .order_by(SystemAuditLog.created_at)
        ).all()
        system_events = [_system_row_to_dict(r) for r in sys_rows]
    except Exception:
        pass

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
                "system_events": system_events,
            }
    except Exception:
        pass

    cached = get_cached_trace(trace_id)
    if cached is not None:
        return {
            "trace_id": trace_id,
            "action": cached["action"],
            "events": cached["events"],
            "system_events": system_events,
        }

    if system_events:
        return {
            "trace_id": trace_id,
            "action": None,
            "events": [],
            "system_events": system_events,
        }

    raise HTTPException(
        status_code=404,
        detail=f"Không tìm thấy dấu vết kiểm toán cho mã trace_id: {trace_id}",
    )


@router.get("/events")
def list_system_audit_events(
    patient_id: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    action_code: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    trace_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Truy vấn danh sách sự kiện kiểm toán toàn hệ thống (`system_audit_logs`) theo bộ lọc."""
    stmt = select(SystemAuditLog)
    if patient_id:
        stmt = stmt.where(SystemAuditLog.patient_id == patient_id)
    if actor_id:
        stmt = stmt.where(SystemAuditLog.actor_id == actor_id)
    if category:
        stmt = stmt.where(SystemAuditLog.category == category)
    if action_code:
        stmt = stmt.where(SystemAuditLog.action_code == action_code)
    if severity:
        stmt = stmt.where(SystemAuditLog.severity == severity)
    if trace_id:
        stmt = stmt.where(SystemAuditLog.trace_id == trace_id)

    stmt = stmt.order_by(desc(SystemAuditLog.created_at), desc(SystemAuditLog.id)).limit(
        limit
    )
    rows = db.scalars(stmt).all()
    return {
        "total": len(rows),
        "events": [_system_row_to_dict(r) for r in rows],
    }


@router.get("/verify-chain")
def verify_system_audit_chain(
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Kiểm định tính toàn vẹn mật mã của chuỗi băm (`prev_hash -> record_hash`) trên bảng `system_audit_logs`."""
    return default_audit_service.verify_chain(db=db, limit=limit)


@router.get("/metrics")
def get_orchestration_metrics() -> Dict[str, Any]:
    """Trả về thống kê độ trễ P50/P95 theo từng nút và bộ đếm sự kiện hàng rào an toàn."""
    return metrics_collector.snapshot()
