"""
Nút kiểm tra đầu ra của mô hình (L5 Output Guard Node).

Ở Giai đoạn 1, nút này cung cấp khung kết nối trong đồ thị và cho phép truyền
hàm đánh giá đầu ra tùy chọn (sẽ nạp đầy đủ 9 quy tắc YAML ở Giai đoạn 4).
"""
from typing import Any, Callable, Dict, Optional

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event


def make_output_guard_node(
    output_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
):
    """Tạo nút `output_guard`: kiểm tra tính an toàn của câu trả lời do LLM sinh ra."""

    @safe_node("output_guard", layer="L5_OUTPUT")
    def output_guard_node(state: AftercareState) -> Dict[str, Any]:
        if output_evaluator is not None:
            return output_evaluator(state)

        text = (state.get("llm_raw_output") or state.get("response_text") or "").strip()
        if not text:
            events = append_guard_event(
                state,
                layer="L5_OUTPUT",
                rule_id="OUT-EMPTY",
                decision="FALLBACK",
                detail="Đầu ra trống sau bước sinh văn bản.",
            )
            return {"output_guard_decision": "FAIL", "guard_events": events}

        events = append_guard_event(
            state,
            layer="L5_OUTPUT",
            rule_id="OUT-DEFAULT-PASS",
            decision="PASSED",
            detail="Đầu ra vượt qua bước kiểm tra cơ bản.",
        )
        return {
            "output_guard_decision": "PASS",
            "response_text": text,
            "guard_events": events,
        }

    return output_guard_node

