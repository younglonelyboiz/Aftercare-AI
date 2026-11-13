"""
Thông điệp an toàn soạn sẵn (Safe Fallback) — [W07-T0.2].

Được trả cho bệnh nhân khi mô hình ngôn ngữ (LLM) hoặc hệ thống gặp sự cố,
thay cho chuỗi lỗi kỹ thuật. Tuân thủ nguyên tắc Fail-safe: không bao giờ
ngầm khẳng định người bệnh an toàn, luôn nhắc dấu hiệu cần gọi cấp cứu 115.
"""

SAFE_FALLBACK_MESSAGE = (
    "Hiện hệ thống chưa thể trả lời câu hỏi này một cách chắc chắn.\n\n"
    "• Nếu Bác/Bạn đang khó thở tăng, nói không thành câu, môi tím hoặc đã xịt thuốc "
    "cắt cơn mà không đỡ: HÃY GỌI NGAY 115 hoặc đến cơ sở y tế gần nhất.\n"
    "• Nếu không khẩn cấp: Bác/Bạn vui lòng thử hỏi lại sau ít phút hoặc liên hệ "
    "điều dưỡng phụ trách để được hỗ trợ.\n\n"
    "Lưu ý y tế: Thông tin chỉ mang tính hỗ trợ, không thay thế chẩn đoán của bác sĩ."
)

