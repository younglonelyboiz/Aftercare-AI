"""
Nút nạp ngữ cảnh bệnh nhân và kiểm tra khóa phiên khẩn cấp (Context & Session Lock Nodes).
"""
from typing import Any, Callable, Dict

from backend.app.orchestration.safe_node import PatientNotFoundError, safe_node
from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)


def make_load_context_node(profile_loader: Callable[[str], Dict[str, Any]]):
    """Tạo nút `load_context`: nạp hồ sơ bệnh nhân theo `patient_id`."""

    @safe_node("load_context", layer="L0_CONTEXT")
    def load_context_node(state: AftercareState) -> Dict[str, Any]:
        patient_id = state.get("patient_id") or ""
        try:
            profile = profile_loader(patient_id)
        except ValueError as exc:
            raise PatientNotFoundError(str(exc)) from exc
        return {"profile": profile or {}}

    return load_context_node


def make_session_lock_check_node():
    """Tạo nút `session_lock_check`: nếu phiên đang khóa ở Vùng Đỏ, nâng rủi ro lên RED_ZONE."""

    @safe_node("session_lock_check", layer="L1_SAFETY")
    def session_lock_check_node(state: AftercareState) -> Dict[str, Any]:
        if state.get("session_locked_red"):
            new_risk = escalate_risk(state.get("risk_level"), "RED_ZONE")
            events = append_guard_event(
                state,
                layer="L1_SAFETY",
                rule_id="SESSION-RED-LOCK",
                decision="ESCALATED",
                detail="Phiên hội thoại đang bị khóa ở chế độ Cờ Đỏ chưa được điều dưỡng đóng.",
            )
            return {"risk_level": new_risk, "guard_events": events}
        return {}

    return session_lock_check_node

