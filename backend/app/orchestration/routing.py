"""
Các hàm định tuyến tất định (Deterministic Conditional Routing) — [W07-T1.5].

Toàn bộ các cạnh rẽ nhánh trong LangGraph StateGraph đều được quyết định bởi
các hàm Python thuần trong tệp này, tuyệt đối không dùng LLM để định tuyến.
"""
from backend.app.orchestration.state import AftercareState


def route_after_load_context(state: AftercareState) -> str:
    """Sau `load_context`: nếu gặp lỗi hệ thống -> `safe_fallback`, ngược lại -> `sanitize_input`."""
    if state.get("error"):
        return "safe_fallback"
    return "sanitize_input"


def route_after_sanitize(state: AftercareState) -> str:
    """Sau `sanitize_input`: nếu gặp lỗi -> `safe_fallback`, luôn đi qua `safety_triage`."""
    if state.get("error"):
        return "safe_fallback"
    return "safety_triage"


def route_after_triage(state: AftercareState) -> str:
    """Sau `safety_triage`:
    - RED_ZONE -> `emergency_response` (bỏ qua LLM)
    - YELLOW_ZONE -> `action_plan_response` (bỏ qua LLM)
    - Lỗi nút -> `safe_fallback`
    - NORMAL -> `session_lock_check`
    """
    if state.get("error"):
        return "safe_fallback"
    risk = state.get("risk_level")
    if risk == "RED_ZONE":
        return "emergency_response"
    if risk == "YELLOW_ZONE":
        return "action_plan_response"
    return "session_lock_check"


def route_after_session_lock(state: AftercareState) -> str:
    """Sau `session_lock_check`: nếu phiên đang khóa Đỏ -> `emergency_response`, ngược lại -> `policy_guard`."""
    if state.get("error"):
        return "safe_fallback"
    if state.get("session_locked_red") or state.get("risk_level") == "RED_ZONE":
        return "emergency_response"
    return "policy_guard"


def route_after_policy(state: AftercareState) -> str:
    """Sau `policy_guard`: nếu BLOCK -> `safe_refusal`, nếu ALLOW -> `retrieve_evidence`."""
    if state.get("error"):
        return "safe_fallback"
    if state.get("policy_decision") == "BLOCK":
        return "safe_refusal"
    return "retrieve_evidence"


def route_after_retrieve(state: AftercareState) -> str:
    """Sau `retrieve_evidence`: nếu thiếu bằng chứng -> `no_evidence_response`, nếu đủ -> `generate_answer`."""
    if state.get("error"):
        return "safe_fallback"
    if state.get("evidence_ok") is False:
        return "no_evidence_response"
    return "generate_answer"


def route_after_generate(state: AftercareState) -> str:
    """Sau `generate_answer`: nếu LLM lỗi/rỗng -> `safe_fallback`, nếu có văn bản -> `output_guard`."""
    if state.get("error") or state.get("degraded"):
        return "safe_fallback"
    if not (state.get("llm_raw_output") or "").strip():
        return "safe_fallback"
    return "output_guard"


def route_after_output_guard(state: AftercareState) -> str:
    """Sau `output_guard`:
    - `RISK_UP` -> `action_plan_response`
    - `FAIL` hoặc có lỗi -> `safe_fallback`
    - `PASS` -> `finalize`
    """
    if state.get("error"):
        return "safe_fallback"
    decision = state.get("output_guard_decision", "PASS")
    if decision == "RISK_UP":
        return "action_plan_response"
    if decision == "FAIL":
        return "safe_fallback"
    return "finalize"

