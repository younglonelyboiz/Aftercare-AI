"""
Nút kiểm tra chính sách đầu vào (L2 Policy Guard Node).

Ở Giai đoạn 1, nút này cung cấp khung kết nối trong đồ thị và cho phép truyền
hàm đánh giá chính sách tùy chọn (sẽ được nạp đầy đủ quy tắc YAML ở Giai đoạn 2).
"""
from typing import Any, Callable, Dict, Optional

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event


def make_policy_guard_node(
    policy_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
):
    """Tạo nút `policy_guard`: đánh giá chính sách đầu vào trên tin nhắn NORMAL."""

    @safe_node("policy_guard", layer="L2_POLICY")
    def policy_guard_node(state: AftercareState) -> Dict[str, Any]:
        if policy_evaluator is not None:
            return policy_evaluator(state)

        events = append_guard_event(
            state,
            layer="L2_POLICY",
            rule_id="POL-DEFAULT-ALLOW",
            decision="PASSED",
            detail="Tin nhắn vượt qua bước kiểm tra chính sách đầu vào.",
        )
        return {"policy_decision": "ALLOW", "guard_events": events}

    return policy_guard_node

