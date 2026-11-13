"""
Nút kiểm tra đầu ra của mô hình ngôn ngữ lớn (L5 Output Guard Node) — [W07-T4.2, T4.3].
"""
from typing import Any, Callable, Dict, Optional

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)


def make_output_guard_node(
    output_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
):
    """Tạo nút `output_guard`: kiểm tra tính an toàn của câu trả lời do LLM sinh ra qua 9 quy tắc YAML."""

    @safe_node("output_guard", layer="L5_OUTPUT")
    def output_guard_node(state: AftercareState) -> Dict[str, Any]:
        if output_evaluator is not None:
            return output_evaluator(state)

        from backend.app.guardrails.output_guard import get_default_output_guard

        verdict = get_default_output_guard().evaluate(state)

        if verdict.decision == "FAIL":
            rule_id = (
                verdict.triggered_rules[0]
                if verdict.triggered_rules
                else "OUT-FAIL"
            )
            events = append_guard_event(
                state,
                layer="L5_OUTPUT",
                rule_id=rule_id,
                decision="BLOCKED",
                detail=verdict.detail,
            )
            return {
                "output_guard_decision": "FAIL",
                "guard_events": events,
            }

        if verdict.decision == "RISK_UP":
            new_risk = escalate_risk(
                state.get("risk_level"),
                verdict.escalated_risk_level or "YELLOW_ZONE",
            )
            events = append_guard_event(
                state,
                layer="L5_OUTPUT",
                rule_id="OUT-RESCREEN",
                decision="ESCALATED",
                detail=verdict.detail,
            )
            return {
                "output_guard_decision": "RISK_UP",
                "risk_level": new_risk,
                "guard_events": events,
            }

        working_state = dict(state)
        events = list(working_state.get("guard_events") or [])
        if verdict.decision == "REWRITTEN":
            for rid in verdict.triggered_rules:
                events = append_guard_event(
                    working_state,  # type: ignore[arg-type]
                    layer="L5_OUTPUT",
                    rule_id=rid,
                    decision="REWRITTEN",
                    detail=verdict.detail,
                )
                working_state["guard_events"] = events
        else:
            events = append_guard_event(
                working_state,  # type: ignore[arg-type]
                layer="L5_OUTPUT",
                rule_id="OUT-ALL-PASS",
                decision="PASSED",
                detail=verdict.detail,
            )

        return {
            "output_guard_decision": "PASS",
            "response_text": verdict.response_text,
            "guard_events": events,
        }

    return output_guard_node
