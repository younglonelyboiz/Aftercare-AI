"""
Các nút sinh phản hồi tất định từ mẫu soạn sẵn (Deterministic Responder Nodes) — [W07-T1.4].

Không nút nào trong tệp này được phép gọi mô hình ngôn ngữ lớn (LLM).
"""
from typing import Any, Dict

from backend.app.guardrails.templates_vi import (
    NO_EVIDENCE_MESSAGE,
    SAFE_FALLBACK_MESSAGE,
    build_emergency_response,
    build_safe_refusal_response,
    build_yellow_zone_response,
)
from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)


def make_emergency_response_node():
    """Tạo nút `emergency_response`: trả hướng dẫn cấp cứu Vùng Đỏ, tuyệt đối không gọi LLM."""

    @safe_node("emergency_response", layer="L1_SAFETY")
    def emergency_response_node(state: AftercareState) -> Dict[str, Any]:
        risk = escalate_risk(state.get("risk_level"), "RED_ZONE")
        text = build_emergency_response(
            state.get("profile") or {},
            patient_id=state.get("patient_id") or "",
        )
        return {
            "risk_level": risk,
            "response_text": text,
            "citations": [],
            "degraded": False,
        }

    return emergency_response_node


def make_action_plan_response_node():
    """Tạo nút `action_plan_response`: trả hướng dẫn xử trí Vùng Vàng, tuyệt đối không gọi LLM."""

    @safe_node("action_plan_response", layer="L1_SAFETY")
    def action_plan_response_node(state: AftercareState) -> Dict[str, Any]:
        risk = escalate_risk(state.get("risk_level"), "YELLOW_ZONE")
        text = build_yellow_zone_response(
            state.get("profile") or {},
            patient_id=state.get("patient_id") or "",
        )
        return {
            "risk_level": risk,
            "response_text": text,
            "citations": [],
            "degraded": False,
        }

    return action_plan_response_node


def make_safe_refusal_node():
    """Tạo nút `safe_refusal`: trả thông điệp từ chối lịch sự khi vi phạm chính sách y tế."""

    @safe_node("safe_refusal", layer="L2_POLICY")
    def safe_refusal_node(state: AftercareState) -> Dict[str, Any]:
        text = build_safe_refusal_response(state.get("policy_reason"))
        return {
            "response_text": text,
            "citations": [],
            "degraded": False,
        }

    return safe_refusal_node


def make_no_evidence_response_node():
    """Tạo nút `no_evidence_response`: trả lời khi không tìm thấy tài liệu đủ độ tin cậy."""

    @safe_node("no_evidence_response", layer="L3_EVIDENCE")
    def no_evidence_response_node(state: AftercareState) -> Dict[str, Any]:
        return {
            "response_text": NO_EVIDENCE_MESSAGE,
            "citations": [],
            "degraded": False,
        }

    return no_evidence_response_node


def make_safe_fallback_node():
    """Tạo nút `safe_fallback`: trả thông điệp an toàn dự phòng khi LLM hoặc hệ thống gặp lỗi."""

    @safe_node("safe_fallback", layer="L4_GENERATION")
    def safe_fallback_node(state: AftercareState) -> Dict[str, Any]:
        events = append_guard_event(
            state,
            layer="L4_GENERATION",
            rule_id="SYS-SAFE-FALLBACK",
            decision="FALLBACK",
            detail="Trả về thông điệp an toàn dự phòng do mô hình hoặc nút xử lý gặp sự cố.",
        )
        return {
            "response_text": SAFE_FALLBACK_MESSAGE,
            "citations": [],
            "degraded": True,
            "guard_events": events,
        }

    return safe_fallback_node

