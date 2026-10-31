from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ScreenerRuleConfig(BaseModel):
    """Cấu hình ngưỡng quy tắc sàng lọc có thể tùy biến bởi nhân viên y tế."""
    personal_best_pef: int = Field(default=450, description="PEF chuẩn cá nhân tốt nhất (L/min)")
    red_pef_ratio: float = Field(default=0.6, description="Ngưỡng PEF vùng đỏ (< 60% mức chuẩn)")
    yellow_pef_ratio: float = Field(default=0.8, description="Ngưỡng PEF vùng vàng (< 80% mức chuẩn)")
    red_spo2_threshold: int = Field(default=92, description="Ngưỡng SpO2 cấp cứu (< 92%)")
    yellow_spo2_threshold: int = Field(default=95, description="Ngưỡng SpO2 cảnh báo (< 95%)")
    max_reliever_puffs_24h: int = Field(default=4, description="Giới hạn số nhát xịt cắt cơn cho phép trong 24h")
    custom_red_keywords: List[str] = Field(default_factory=list, description="Từ khóa cờ đỏ cấp cứu bổ sung")
    custom_yellow_keywords: List[str] = Field(default_factory=list, description="Từ khóa cảnh báo hen trở nặng bổ sung")

class ScreenerInput(BaseModel):
    """Dữ liệu đầu vào hybrid cho Symptom Screener Engine."""
    patient_id: Optional[str] = None
    free_text: Optional[str] = Field(default=None, description="Đoạn văn bản chat hoặc mô tả triệu chứng tự do")
    pef_value: Optional[int] = Field(default=None, description="Chỉ số PEF thực tế đo được (L/min)")
    spo2: Optional[int] = Field(default=None, description="Chỉ số SpO2 thực tế đo được (%)")
    reliever_puffs: Optional[int] = Field(default=0, description="Số nhát thuốc cắt cơn đã dùng trong 24h gần nhất")
    selected_symptoms: List[str] = Field(default_factory=list, description="Danh mục mã triệu chứng được tick chọn")
    config_override: Optional[ScreenerRuleConfig] = Field(default=None, description="Cấu hình ngưỡng cá nhân hóa ghi đè")

class ScreenerResult(BaseModel):
    """Kết quả sàng lọc phân tầng nguy cơ - Tuyệt đối không chẩn đoán bệnh học."""
    risk_level: Literal["RED_ZONE", "YELLOW_ZONE", "NORMAL"]
    matched_flags: List[str] = Field(default_factory=list, description="Danh mục mã cờ nguy cơ được kích hoạt")
    matched_reasons: List[str] = Field(default_factory=list, description="Diễn giải lâm sàng khách quan về dấu hiệu ghi nhận")
    action_instructions: str = Field(..., description="Chỉ dẫn hành động ứng phó tức thời theo Action Plan")
    escalate_to_staff: bool = Field(..., description="Cờ cảnh báo yêu cầu nhân viên y tế can thiệp/theo dõi")
    suggested_follow_up_minutes: Optional[int] = Field(default=None, description="Thời gian đề xuất đánh giá lại (phút)")
    disclaimer: str = Field(
        default=(
            "Lưu ý y tế: Kết quả sàng lọc chỉ nhằm đánh giá mức độ khẩn cấp và "
            "hướng dẫn xử trí ban đầu, tuyệt đối không thay thế chẩn đoán của bác sĩ chuyên khoa."
        ),
        description="Tuyên bố từ chối trách nhiệm chẩn đoán y khoa bắt buộc"
    )
