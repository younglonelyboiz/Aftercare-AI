"""
Nút làm sạch đầu vào (L0 Input Sanitizer Node).
"""
import re
import unicodedata
from typing import Any, Dict

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event

MAX_INPUT_CHARS = 2000
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\ufeff]")


def make_sanitize_input_node():
    """Tạo nút `sanitize_input`: chuẩn hóa Unicode NFC, lọc ký tự điều khiển và giới hạn độ dài."""

    @safe_node("sanitize_input", layer="L0_SANITIZE")
    def sanitize_input_node(state: AftercareState) -> Dict[str, Any]:
        raw = state.get("raw_message") or ""
        normalized = unicodedata.normalize("NFC", raw)
        cleaned = CONTROL_CHAR_RE.sub("", normalized).strip()
        events = list(state.get("guard_events") or [])

        if len(cleaned) > MAX_INPUT_CHARS:
            cleaned = cleaned[:MAX_INPUT_CHARS]
            events = append_guard_event(
                state,
                layer="L0_SANITIZE",
                rule_id="IN-LEN",
                decision="REWRITTEN",
                detail=f"Tin nhắn vượt {MAX_INPUT_CHARS} ký tự, đã cắt bớt phần dư.",
            )
        else:
            events = append_guard_event(
                state,
                layer="L0_SANITIZE",
                rule_id="IN-SANITIZE",
                decision="PASSED",
                detail="Đã chuẩn hóa chuỗi đầu vào.",
            )

        return {"clean_message": cleaned, "guard_events": events}

    return sanitize_input_node

