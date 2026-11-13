"""
Nút kiểm tra chính sách đầu vào (L2 Policy Guard Node) — [W07-T2.3].

Thực thi `InputPolicyGuard` (nạp từ `input_policies.yaml`) khi không có
`policy_evaluator` tùy chỉnh được truyền vào.
"""
from typing import Any, Callable, Dict, Optional

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event

_default_input_guard: Optional[Any] = None


def get_default_input_guard():
    global _default_input_guard
    if _default_input_guard is None:
        from backend.app.guardrails.input_guard import InputPolicyGuard

        _default_input_guard = InputPolicyGuard()
    return _default_input_guard


def make_policy_guard_node(
    policy_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
):
    """Tạo nút `policy_guard`: đánh giá chính sách đầu vào trên tin nhắn NORMAL."""

    @safe_node("policy_guard", layer="L2_POLICY")
    def policy_guard_node(state: AftercareState) -> Dict[str, Any]:
        if policy_evaluator is not None:
            return policy_evaluator(state)

        text = state.get("clean_message") or state.get("raw_message") or ""
        guard = get_default_input_guard()
        match = guard.evaluate_text(text)

        if match.decision == "BLOCK":
            events = append_guard_event(
                state,
                layer="L2_POLICY",
                rule_id=match.rule_id,
                decision="BLOCKED",
                detail=f"Chặn bởi quy tắc {match.rule_id} ({match.rule_name}).",
            )
            return {
                "policy_decision": "BLOCK",
                "policy_rule_id": match.rule_id,
                "policy_reason": match.response_text,
                "policy_escalation": match.escalation,
                "guard_events": events,
            }

        events = append_guard_event(
            state,
            layer="L2_POLICY",
            rule_id=match.rule_id,
            decision="PASSED",
            detail="Tin nhắn vượt qua bước kiểm tra chính sách đầu vào.",
        )
        return {
            "policy_decision": "ALLOW",
            "policy_rule_id": match.rule_id,
            "policy_reason": None,
            "policy_escalation": None,
            "guard_events": events,
        }

    return policy_guard_node
