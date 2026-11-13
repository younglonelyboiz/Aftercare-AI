"""
Nút hoàn tất phản hồi và ghi nhận kiểm toán (Finalize & Audit Nodes).
"""
import logging
from typing import Any, Dict

from backend.app.guardrails.templates_vi import SAFE_FALLBACK_MESSAGE
from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState

logger = logging.getLogger("OrchestrationAudit")


def make_finalize_node():
    """Tạo nút `finalize`: bảo đảm luôn có chuỗi phản hồi hợp lệ trước khi kết thúc."""

    @safe_node("finalize", layer="L7_AUDIT")
    def finalize_node(state: AftercareState) -> Dict[str, Any]:
        text = (state.get("response_text") or "").strip()
        if not text:
            return {
                "response_text": SAFE_FALLBACK_MESSAGE,
                "citations": [],
                "degraded": True,
            }
        return {}

    return finalize_node


def make_audit_node():
    """Tạo nút `audit`: ghi nhật ký hành động và độ trễ của từng nút trong lượt xử lý."""

    @safe_node("audit", layer="L7_AUDIT")
    def audit_node(state: AftercareState) -> Dict[str, Any]:
        logger.info(
            "trace_id=%s patient_id=%s risk=%s degraded=%s events=%d latency_ms=%s",
            state.get("trace_id"),
            state.get("patient_id"),
            state.get("risk_level"),
            state.get("degraded"),
            len(state.get("guard_events") or []),
            state.get("latency_ms"),
        )
        return {}

    return audit_node

