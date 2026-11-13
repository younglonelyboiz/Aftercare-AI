"""
Bộ ẩn danh thông tin định danh cá nhân (PII Redactor) — [W07-T3.3].

Thực thi bất biến INV-6 (No PII Egress):
- Thay thế họ và tên bệnh nhân (`full_name`) bằng `"Người bệnh"`.
- Loại bỏ mã bệnh nhân (`BN-...`), số điện thoại, địa chỉ thư điện tử, số căn cước/bảo hiểm,
  và địa chỉ cư trú chi tiết trước khi gửi bất kỳ chuỗi nào tới nhà cung cấp LLM bên ngoài.
- Chỉ giữ lại các trường lâm sàng tối thiểu (nhóm tuổi, chẩn đoán, chỉ số PEF/SpO2, danh sách
  thuốc trong kế hoạch điều trị và ghi nhớ hội thoại đã che PII).
"""
import copy
import re
from typing import Any, Dict, List, Optional

# 1. Mẫu nhận diện mã hồ sơ bệnh nhân (ví dụ: BN-2026-ASTHMA-01, BN-TEST-01)
_RE_PATIENT_ID = re.compile(r"\bBN-[A-Za-z0-9_-]{2,40}\b", re.IGNORECASE)

# 2. Mẫu nhận diện số điện thoại Việt Nam (di động 10 số, cố định 10-11 số, đầu +84 / 84 / 0)
_RE_PHONE = re.compile(
    r"(?<!\d)(?:\+?84|0)(?:[\s.\-]*\d){8,10}(?!\d)"
)

# 3. Mẫu nhận diện địa chỉ thư điện tử (Email)
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# 4. Mẫu nhận diện số CCCD / CMND / mã định danh công dân (9 đến 12 chữ số liên tiếp)
_RE_NATIONAL_ID = re.compile(r"(?<!\d)\d{9,12}(?!\d)")

# 5. Mẫu nhận diện địa chỉ nhà chi tiết bằng tiếng Việt
_RE_STREET_ADDRESS = re.compile(
    r"(?i)\b(?:số\s+nhà|địa\s+chỉ\s*[:\-]?|ngõ|ngách|hẻm)\s+\d+[A-Za-z0-9/\s,.\-]{3,60}"
)

# Các khóa nhạy cảm trong dict cần xóa hoặc che trực tiếp
_SENSITIVE_KEYS = {
    "patient_id",
    "phone",
    "phone_number",
    "so_dien_thoai",
    "email",
    "address",
    "dia_chi",
    "cccd",
    "cmnd",
    "national_id",
    "bhyt",
    "insurance_id",
    "owner_user_id",
    "source_message_id",
    "conversation_id",
}


def _age_to_group(age: Any) -> str:
    """Chuyển tuổi chính xác thành nhóm tuổi lâm sàng."""
    try:
        val = int(age)
    except (TypeError, ValueError):
        return "Không rõ"
    if val < 12:
        return "Trẻ em (<12 tuổi)"
    if val < 18:
        return "Vị thành niên (12-17 tuổi)"
    if val < 40:
        return "Người trưởng thành trẻ (18-39 tuổi)"
    if val < 60:
        return "Trung niên (40-59 tuổi)"
    return "Người cao tuổi (>=60 tuổi)"


class PIIRedactor:
    """Bộ lọc ẩn danh thông tin định danh cá nhân trước khi gọi LLM (INV-6)."""

    def _extract_sensitive_literals(
        self, profile: Optional[Dict[str, Any]]
    ) -> List[tuple[str, str]]:
        """Trích xuất các chuỗi định danh cụ thể từ hồ sơ bệnh nhân để thay thế chính xác."""
        replacements: List[tuple[str, str]] = []
        if not isinstance(profile, dict):
            return replacements

        p_info = profile.get("patient_info") or {}
        if isinstance(p_info, dict):
            full_name = str(p_info.get("full_name") or "").strip()
            if full_name and full_name.lower() != "người bệnh":
                replacements.append((full_name, "Người bệnh"))

            pid = str(p_info.get("patient_id") or "").strip()
            if pid:
                replacements.append((pid, "[MÃ_BỆNH_NHÂN]"))

            addr = str(p_info.get("address") or p_info.get("dia_chi") or "").strip()
            if addr:
                replacements.append((addr, "[ĐỊA_CHỈ]"))

            phone = str(p_info.get("phone") or p_info.get("phone_number") or "").strip()
            if phone:
                replacements.append((phone, "[SỐ_ĐIỆN_THOẠI]"))

        top_pid = str(profile.get("patient_id") or "").strip()
        if top_pid:
            replacements.append((top_pid, "[MÃ_BỆNH_NHÂN]"))

        return replacements

    def redact_text(
        self,
        text: Optional[str],
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Ẩn danh mọi thông tin định danh cá nhân xuất hiện trong chuỗi văn bản."""
        if not text:
            return ""
        cleaned = str(text)

        # 1. Thay thế các chuỗi cụ thể từ hồ sơ bệnh nhân (họ tên, mã bệnh nhân, địa chỉ)
        for literal, mask in self._extract_sensitive_literals(profile):
            if literal:
                pattern = re.compile(re.escape(literal), re.IGNORECASE)
                cleaned = pattern.sub(mask, cleaned)

        # 2. Thay thế theo mẫu biểu thức chính quy
        cleaned = _RE_PATIENT_ID.sub("[MÃ_BỆNH_NHÂN]", cleaned)
        cleaned = _RE_EMAIL.sub("[EMAIL]", cleaned)
        cleaned = _RE_PHONE.sub("[SỐ_ĐIỆN_THOẠI]", cleaned)
        cleaned = _RE_NATIONAL_ID.sub("[MÃ_ĐỊNH_DANH]", cleaned)
        cleaned = _RE_STREET_ADDRESS.sub("[ĐỊA_CHỈ]", cleaned)

        return cleaned

    def _scrub_value(
        self,
        value: Any,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if isinstance(value, str):
            return self.redact_text(value, profile=profile)
        if isinstance(value, list):
            return [self._scrub_value(item, profile=profile) for item in value]
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for k, v in value.items():
                key_lower = str(k).lower()
                if key_lower in _SENSITIVE_KEYS:
                    continue
                if key_lower == "full_name":
                    result[k] = "Người bệnh"
                elif key_lower == "age":
                    result["age_group"] = _age_to_group(v)
                else:
                    result[k] = self._scrub_value(v, profile=profile)
            return result
        return value

    def redact_profile(
        self, profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tạo bản sao hồ sơ lâm sàng tối thiểu đã loại bỏ hoàn toàn PII."""
        if not isinstance(profile, dict) or not profile:
            return {}
        copied = copy.deepcopy(profile)
        return self._scrub_value(copied, profile=profile)

    def redact_memory(
        self,
        memory: Optional[Dict[str, Any]],
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ẩn danh PII trong tóm tắt hội thoại cũ và ghi nhớ dài hạn."""
        if not isinstance(memory, dict) or not memory:
            return {}
        copied = copy.deepcopy(memory)
        return self._scrub_value(copied, profile=profile)

    def redact_history(
        self,
        history: Optional[List[Dict[str, str]]],
        profile: Optional[Dict[str, Any]] = None,
        max_turns: int = 5,
    ) -> List[Dict[str, str]]:
        """Lấy tối đa `max_turns` lượt gần nhất (mỗi lượt gồm user + assistant) và ẩn danh PII."""
        if not history:
            return []
        max_messages = max(1, max_turns * 2)
        recent_slice = list(history)[-max_messages:]
        sanitized: List[Dict[str, str]] = []
        for turn in recent_slice:
            role = str(turn.get("role") or "user")
            content = self.redact_text(str(turn.get("content") or ""), profile=profile)
            if content.strip():
                sanitized.append({"role": role, "content": content})
        return sanitized

    def contains_pii(
        self,
        payload_text: str,
        profile: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Kiểm tra xem một chuỗi payload có còn sót thông tin định danh cá nhân hay không."""
        if not payload_text:
            return []
        findings: List[str] = []
        for literal, mask in self._extract_sensitive_literals(profile):
            if literal and re.search(re.escape(literal), payload_text, re.IGNORECASE):
                findings.append(f"literal:{mask}")
        if _RE_PATIENT_ID.search(payload_text):
            findings.append("patient_id")
        if _RE_EMAIL.search(payload_text):
            findings.append("email")
        if _RE_PHONE.search(payload_text):
            findings.append("phone")
        if _RE_NATIONAL_ID.search(payload_text):
            findings.append("national_id")
        if _RE_STREET_ADDRESS.search(payload_text):
            findings.append("street_address")
        return findings


default_pii_redactor = PIIRedactor()

__all__ = ["PIIRedactor", "default_pii_redactor"]

