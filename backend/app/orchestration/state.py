"""
Định nghĩa trạng thái đồ thị điều phối (AftercareState) và bất biến rủi ro đơn điệu (INV-1) — [W07-T1.2].
"""
import uuid
from typing import Any, Dict, List, Literal, Optional, TypedDict

RiskLevel = Literal["NORMAL", "YELLOW_ZONE", "RED_ZONE"]
GuardDecision = Literal["PASSED", "BLOCKED", "ESCALATED", "REWRITTEN", "FALLBACK"]

RISK_ORDER: Dict[str, int] = {
    "NORMAL": 0,
    "YELLOW_ZONE": 1,
    "RED_ZONE": 2,
}


class RiskDowngradeError(RuntimeError):
    """Ngoại lệ ném ra khi có hành vi hạ mức rủi ro y tế trong cùng một lượt xử lý (vi phạm INV-1)."""


class GuardEvent(TypedDict):
    """Sự kiện kiểm toán tại một chốt chặn an toàn (Guardrail)."""

    layer: str
    rule_id: str
    decision: GuardDecision
    detail: str


class AftercareState(TypedDict, total=False):
    """Trạng thái dùng chung đi qua toàn bộ các nút (node) của LangGraph StateGraph."""

    trace_id: str
    session_id: str
    patient_id: str
    channel: Literal["CHAT", "CHECKIN"]
    raw_message: str
    clean_message: str
    model_override: Optional[str]
    profile: Dict[str, Any]
    care_plan_day: Optional[int]
    history: List[Dict[str, str]]
    memory: Dict[str, Any]
    session_locked_red: bool
    screener_result: Dict[str, Any]
    risk_level: RiskLevel
    policy_decision: Literal["ALLOW", "BLOCK"]
    policy_rule_id: Optional[str]
    policy_reason: Optional[str]
    retrieved_chunks: List[Dict[str, Any]]
    evidence_ok: bool
    llm_raw_output: Optional[str]
    output_guard_decision: Literal["PASS", "FAIL", "RISK_UP"]
    response_text: str
    citations: List[Dict[str, Any]]
    degraded: bool
    ticket_id: Optional[str]
    guard_events: List[GuardEvent]
    latency_ms: Dict[str, int]
    error: Optional[str]


def escalate_risk(current_level: Optional[RiskLevel], new_level: RiskLevel) -> RiskLevel:
    """Cập nhật mức rủi ro theo nguyên tắc đơn điệu tăng (INV-1: Monotonic Risk).

    Mức rủi ro chỉ được giữ nguyên hoặc tăng từ NORMAL -> YELLOW_ZONE -> RED_ZONE.
    Mọi nỗ lực hạ mức rủi ro trong cùng một lượt đều ném `RiskDowngradeError`.
    """
    if new_level not in RISK_ORDER:
        raise ValueError(f"Mức rủi ro không hợp lệ: {new_level}")
    if current_level is None:
        return new_level
    if current_level not in RISK_ORDER:
        raise ValueError(f"Mức rủi ro hiện tại không hợp lệ: {current_level}")
    if RISK_ORDER[new_level] < RISK_ORDER[current_level]:
        raise RiskDowngradeError(
            f"Vi phạm bất biến INV-1: không được phép hạ mức rủi ro từ {current_level} xuống {new_level}."
        )
    return new_level


def append_guard_event(
    state: AftercareState,
    layer: str,
    rule_id: str,
    decision: GuardDecision,
    detail: str,
) -> List[GuardEvent]:
    """Tạo danh sách guard_events mới có nối thêm một sự kiện kiểm toán."""
    events = list(state.get("guard_events") or [])
    events.append(
        GuardEvent(
            layer=layer,
            rule_id=rule_id,
            decision=decision,
            detail=detail,
        )
    )
    return events


def make_initial_state(
    patient_id: str,
    message: str,
    session_id: Optional[str] = None,
    model_override: Optional[str] = None,
    channel: Literal["CHAT", "CHECKIN"] = "CHAT",
) -> AftercareState:
    """Khởi tạo trạng thái ban đầu cho một lượt xử lý trên đồ thị."""
    return AftercareState(
        trace_id=f"trace-{uuid.uuid4().hex[:12]}",
        session_id=session_id or f"sess-{patient_id}",
        patient_id=patient_id,
        channel=channel,
        raw_message=message or "",
        clean_message=(message or "").strip(),
        model_override=model_override,
        profile={},
        care_plan_day=None,
        history=[],
        memory={},
        session_locked_red=False,
        screener_result={"matched_flags": [], "matched_reasons": []},
        risk_level="NORMAL",
        policy_decision="ALLOW",
        policy_rule_id=None,
        policy_reason=None,
        retrieved_chunks=[],
        evidence_ok=True,
        llm_raw_output=None,
        output_guard_decision="PASS",
        response_text="",
        citations=[],
        degraded=False,
        ticket_id=None,
        guard_events=[],
        latency_ms={},
        error=None,
    )

