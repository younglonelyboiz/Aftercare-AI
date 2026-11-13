"""
Nút phân loại an toàn y tế (L1 Safety Triage Node) — chạy độc lập trước mọi lời gọi LLM.
"""
from typing import Any, Callable, Dict

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)


def make_safety_triage_node(screener_fn: Callable[[str, Dict[str, Any]], Any]):
    """Tạo nút `safety_triage`: gọi hàm sàng lọc trên văn bản gốc trước khi bị cắt ngắn."""

    @safe_node("safety_triage", layer="L1_SAFETY")
    def safety_triage_node(state: AftercareState) -> Dict[str, Any]:
        text_for_triage = state.get("raw_message") or state.get("clean_message") or ""
        profile = state.get("profile") or {}

        screener_res = screener_fn(text_for_triage, profile)
        if isinstance(screener_res, str):
            evaluated_level = screener_res
            matched_flags = []
            matched_reasons = []
        else:
            evaluated_level = getattr(screener_res, "risk_level", "NORMAL")
            matched_flags = list(getattr(screener_res, "matched_flags", []) or [])
            matched_reasons = list(getattr(screener_res, "matched_reasons", []) or [])

        new_risk = escalate_risk(state.get("risk_level"), evaluated_level)
        decision = "ESCALATED" if new_risk in ("RED_ZONE", "YELLOW_ZONE") else "PASSED"
        rule_id = (
            "ASTHMA-RED-01"
            if new_risk == "RED_ZONE"
            else ("ASTHMA-YEL-01" if new_risk == "YELLOW_ZONE" else "ASTHMA-GRN-01")
        )
        detail = (
            "; ".join(matched_reasons)
            if matched_reasons
            else f"Phân tầng an toàn: {new_risk}"
        )
        events = append_guard_event(
            state,
            layer="L1_SAFETY",
            rule_id=rule_id,
            decision=decision,
            detail=detail,
        )

        return {
            "risk_level": new_risk,
            "screener_result": {
                "matched_flags": matched_flags,
                "matched_reasons": matched_reasons,
            },
            "guard_events": events,
        }

    return safety_triage_node
