"""
Bộ mẫu phản hồi lâm sàng soạn sẵn bằng tiếng Việt (Deterministic Clinical Templates) — [W07-T1.4].

Tất cả các phản hồi ở Vùng Đỏ, Vùng Vàng, từ chối theo chính sách an toàn, thiếu bằng chứng
và dự phòng sự cố đều được xuất ra từ tệp này mà không đi qua mô hình ngôn ngữ lớn (LLM).
"""
from typing import Any, Dict, Optional

from backend.app.rag.safe_messages import SAFE_FALLBACK_MESSAGE

DEFAULT_RED_ACTION = (
    "Sử dụng ngay 2-4 nhát thuốc cắt cơn qua buồng đệm. "
    "Nếu không cải thiện sau 5 phút, lặp lại liều và gọi 115 cấp cứu ngay."
)
DEFAULT_YELLOW_ACTION = (
    "Dùng ngay 2 nhát thuốc cắt cơn, nghỉ ngơi tại chỗ trong môi trường thoáng khí "
    "và đo lại PEF sau 20 phút."
)

EMPTY_INPUT_MESSAGE = (
    "Bác/Bạn chưa nhập nội dung câu hỏi hoặc triệu chứng. "
    "Vui lòng nhập câu hỏi hoặc mô tả tình trạng hô hấp hiện tại để hệ thống hỗ trợ."
)

NO_EVIDENCE_MESSAGE = (
    "Tài liệu hướng dẫn lâm sàng hiện có trong hệ thống chưa đề cập trực tiếp đến vấn đề này.\n"
    "Bác/Bạn vui lòng trao đổi trực tiếp với bác sĩ điều trị hoặc điều dưỡng phụ trách "
    "để được tư vấn chính xác.\n\n"
    "Lưu ý y tế: Thông tin chỉ mang tính hỗ trợ, không thay thế chẩn đoán của bác sĩ."
)

DEFAULT_REFUSAL_MESSAGE = (
    "Vì lý do an toàn y tế, Trợ lý Aftercare-AI không được phép tự ý chẩn đoán bệnh mới, "
    "kê đơn thuốc hoặc thay đổi liều lượng trong đơn xuất viện của bác sĩ.\n"
    "Bác/Bạn vui lòng tiếp tục dùng thuốc đúng theo Kế hoạch hành động hen và liên hệ "
    "điều dưỡng hoặc bác sĩ điều trị để được tư vấn cụ thể.\n\n"
    "Lưu ý y tế: Thông tin chỉ mang tính hỗ trợ, không thay thế chẩn đoán của bác sĩ."
)


def _extract_profile_fields(
    profile: Dict[str, Any], patient_id: str = ""
) -> Dict[str, str]:
    p_info = profile.get("patient_info", {}) or {}
    meds = profile.get("current_medications", {}) or {}
    plan = profile.get("action_plan_rules", {}) or {}
    follow = profile.get("follow_up", {}) or {}

    return {
        "patient_name": p_info.get("full_name") or f"Bệnh nhân {patient_id}",
        "reliever_med": meds.get(
            "reliever_med", "Thuốc cắt cơn dạng hít/xịt (Salbutamol/Ventolin)"
        ),
        "hospital_name": follow.get(
            "hospital", "Bệnh viện Phổi hoặc cơ sở y tế gần nhất"
        ),
        "red_action": plan.get("red_zone") or DEFAULT_RED_ACTION,
        "yellow_action": plan.get("yellow_zone") or DEFAULT_YELLOW_ACTION,
    }


def build_emergency_response(profile: Dict[str, Any], patient_id: str = "") -> str:
    """Sinh phản hồi cứng cho Vùng Đỏ (RED_ZONE) theo hồ sơ bệnh nhân."""
    fields = _extract_profile_fields(profile, patient_id=patient_id)
    return (
        f"CẢNH BÁO CỜ ĐỎ CẤP CỨU: Bác/Bạn {fields['patient_name']} đang có dấu hiệu NGUY KỊCH!\n\n"
        f"1. GỌI NGAY CẤP CỨU 115: Nhờ người thân gọi ngay Cấp cứu 115 hoặc di chuyển khẩn cấp tới {fields['hospital_name']}!\n"
        f"2. DÙNG NGAY THUỐC CẮT CƠN: Sử dụng ngay {fields['reliever_med']} theo đúng kế hoạch hành động: {fields['red_action']}\n"
        f"3. TƯ THẾ AN TOÀN: Ngồi thẳng lưng, hơi cúi người ra phía trước, thở chúm môi chậm rãi. TUYỆT ĐỐI KHÔNG NẰM NGỬA!\n\n"
        f"Hệ thống đã gửi báo động khẩn cấp đến điều dưỡng trực."
    )


def build_yellow_zone_response(profile: Dict[str, Any], patient_id: str = "") -> str:
    """Sinh phản hồi cứng cho Vùng Vàng (YELLOW_ZONE) theo hồ sơ bệnh nhân."""
    fields = _extract_profile_fields(profile, patient_id=patient_id)
    return (
        f"CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Bác/Bạn {fields['patient_name']} đang có dấu hiệu hen bùng phát hoặc kiểm soát kém.\n\n"
        f"1. DÙNG THUỐC CẮT CƠN: Dùng ngay {fields['reliever_med']} theo đúng chỉ định Vùng Vàng: {fields['yellow_action']}\n"
        f"2. NGHỈ NGƠI TẠI CHỖ: Tránh xa môi trường khói bụi, máy lạnh hoặc tác nhân dị nguyên.\n"
        f"3. THEO DÕI ĐÁNH GIÁ LẠI: Sau 20-30 phút nếu cơn khó thở không giảm hoặc xuất hiện dấu hiệu nguy cấp, cần liên hệ cơ sở y tế ({fields['hospital_name']}) ngay.\n\n"
        f"Điều dưỡng phụ trách đã được thông báo để theo dõi."
    )


def build_safe_refusal_response(reason: Optional[str] = None) -> str:
    """Sinh phản hồi từ chối an toàn khi câu hỏi vi phạm chính sách y tế (L2 Policy Guard)."""
    if reason and reason.strip():
        return reason
    return DEFAULT_REFUSAL_MESSAGE


__all__ = [
    "DEFAULT_RED_ACTION",
    "DEFAULT_YELLOW_ACTION",
    "DEFAULT_REFUSAL_MESSAGE",
    "EMPTY_INPUT_MESSAGE",
    "NO_EVIDENCE_MESSAGE",
    "SAFE_FALLBACK_MESSAGE",
    "build_emergency_response",
    "build_safe_refusal_response",
    "build_yellow_zone_response",
]

