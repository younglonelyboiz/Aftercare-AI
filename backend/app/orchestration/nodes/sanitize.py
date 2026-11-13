"""
Nút làm sạch đầu vào (L0 Input Sanitizer Node) — [W07-T2.1].

Thực thi 3 quy tắc tất định:
- `IN-CTRL`: Loại bỏ ký tự điều khiển, zero-width và chuẩn hóa các ký tự đồng hình (homoglyph)
  về bảng chữ cái chuẩn kèm chuẩn hóa Unicode NFC.
- `IN-EMPTY`: Phát hiện chuỗi rỗng hoặc chỉ chứa ký tự trắng, đánh dấu `input_empty=True`.
- `IN-LEN`: Giới hạn `clean_message` tối đa 2.000 ký tự, trong khi vẫn giữ văn bản đầy đủ đã
  khử ký tự ẩn trong `raw_message` để nút `safety_triage` quét toàn bộ triệu chứng.
"""
import re
import unicodedata
from typing import Any, Dict

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event

MAX_INPUT_CHARS = 2000
CONTROL_AND_ZW_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]"
)

# Bảng ánh xạ các ký tự đồng hình (Cyrillic / Hy Lạp giống chữ Latin) thường dùng để lách bộ lọc
HOMOGLYPH_MAP = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "і": "i",
        "ј": "j",
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "Х": "X",
        "І": "I",
    }
)


def sanitize_text_preserve_length(text: str) -> str:
    """Chuẩn hóa NFKC + NFC, chuyển ký tự đồng hình và loại bỏ ký tự điều khiển/zero-width."""
    if not text:
        return ""
    compatible = unicodedata.normalize("NFKC", text)
    dehomoglyphed = compatible.translate(HOMOGLYPH_MAP)
    normalized = unicodedata.normalize("NFC", dehomoglyphed)
    return CONTROL_AND_ZW_RE.sub("", normalized)


def make_sanitize_input_node():
    """Tạo nút `sanitize_input`: chuẩn hóa văn bản, kiểm tra rỗng và giới hạn độ dài."""

    @safe_node("sanitize_input", layer="L0_SANITIZE")
    def sanitize_input_node(state: AftercareState) -> Dict[str, Any]:
        raw = state.get("raw_message") or ""
        cleaned_full = sanitize_text_preserve_length(raw).strip()

        if not cleaned_full:
            events = append_guard_event(
                state,
                layer="L0_SANITIZE",
                rule_id="IN-EMPTY",
                decision="BLOCKED",
                detail="Tin nhắn rỗng hoặc chỉ chứa ký tự trắng/ký tự điều khiển.",
            )
            return {
                "raw_message": "",
                "clean_message": "",
                "input_empty": True,
                "guard_events": events,
            }

        if len(cleaned_full) > MAX_INPUT_CHARS:
            truncated = cleaned_full[:MAX_INPUT_CHARS]
            events = append_guard_event(
                state,
                layer="L0_SANITIZE",
                rule_id="IN-LEN",
                decision="REWRITTEN",
                detail=f"Tin nhắn vượt {MAX_INPUT_CHARS} ký tự, đã cắt bớt phần dư cho bước hỏi đáp.",
            )
            return {
                "raw_message": cleaned_full,
                "clean_message": truncated,
                "input_empty": False,
                "guard_events": events,
            }

        rule_decision = "REWRITTEN" if cleaned_full != raw.strip() else "PASSED"
        events = append_guard_event(
            state,
            layer="L0_SANITIZE",
            rule_id="IN-CTRL" if rule_decision == "REWRITTEN" else "IN-SANITIZE",
            decision=rule_decision,
            detail="Đã chuẩn hóa chuỗi đầu vào.",
        )
        return {
            "raw_message": cleaned_full,
            "clean_message": cleaned_full,
            "input_empty": False,
            "guard_events": events,
        }

    return sanitize_input_node
