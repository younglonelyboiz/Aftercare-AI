"""
Nút nạp ngữ cảnh bệnh nhân và kiểm tra khóa phiên khẩn cấp (Context & Session Lock Nodes) — [W07-T3.5, T3.6].
"""
from typing import Any, Callable, Dict

from backend.app.orchestration.safe_node import PatientNotFoundError, safe_node
from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)


def _has_unresolved_p0_ticket(profile: Dict[str, Any]) -> bool:
    """Kiểm tra hồ sơ lâm sàng hiện tại có vé cảnh báo P0_CRITICAL chưa RESOLVED hay không."""
    if not isinstance(profile, dict):
        return False
    active_alerts = profile.get("active_alerts")
    if not isinstance(active_alerts, list):
        return False
    for alert in active_alerts:
        if not isinstance(alert, dict):
            continue
        priority = str(alert.get("priority") or "").upper()
        status = str(alert.get("status") or "OPEN").upper()
        if priority == "P0_CRITICAL" and status in ("OPEN", "ACKNOWLEDGED"):
            return True
    return False


def make_load_context_node(profile_loader: Callable[[str], Dict[str, Any]]):
    """Tạo nút `load_context`: nạp hồ sơ bệnh nhân theo `patient_id` nếu chưa được truyền sẵn."""

    @safe_node("load_context", layer="L0_CONTEXT")
    def load_context_node(state: AftercareState) -> Dict[str, Any]:
        existing_profile = state.get("profile")
        if existing_profile:
            profile = existing_profile
        else:
            patient_id = state.get("patient_id") or ""
            try:
                profile = profile_loader(patient_id) or {}
            except ValueError as exc:
                raise PatientNotFoundError(str(exc)) from exc

        updates: Dict[str, Any] = {"profile": profile}
        if _has_unresolved_p0_ticket(profile):
            updates["session_locked_red"] = True
        return updates

    return load_context_node


def make_session_lock_check_node():
    """Tạo nút `session_lock_check` [W07-T3.6]:
    Nếu phiên đang có cờ `session_locked_red`, hoặc hồ sơ có vé `P0_CRITICAL` chưa `RESOLVED`,
    hoặc lượt trước trong phiên là `RED_ZONE` (khi chưa có xác nhận đóng vé), giữ nguyên chế độ
    cấp cứu `RED_ZONE` và không gọi LLM."""

    @safe_node("session_lock_check", layer="L1_SAFETY")
    def session_lock_check_node(state: AftercareState) -> Dict[str, Any]:
        profile = state.get("profile") or {}
        memory = state.get("memory") or {}

        has_p0 = _has_unresolved_p0_ticket(profile)
        memory_red = (
            "active_alerts" not in profile
            and str(memory.get("last_safety_status") or "").upper() == "RED_ZONE"
        )
        locked = bool(state.get("session_locked_red")) or has_p0 or memory_red

        if locked:
            new_risk = escalate_risk(state.get("risk_level"), "RED_ZONE")
            events = append_guard_event(
                state,
                layer="L1_SAFETY",
                rule_id="SESSION-RED-LOCK",
                decision="ESCALATED",
                detail=(
                    "Phiên hội thoại đang khóa ở chế độ Cờ Đỏ do có cảnh báo P0_CRITICAL "
                    "chưa được điều dưỡng đóng (RESOLVED)."
                ),
            )
            return {
                "session_locked_red": True,
                "risk_level": new_risk,
                "guard_events": events,
            }
        return {}

    return session_lock_check_node
