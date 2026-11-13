from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

# [W07-T5.1] Danh sách mã loại cảnh báo sinh từ luồng hội thoại Chatbot và nhãn hiển thị tiếng Việt
CHAT_ALERT_TYPES = {
    "CHAT_RED_FLAG_DETECTION",
    "CHAT_YELLOW_ZONE_ALERT",
    "MEDICATION_NONADHERENCE_INTENT",
    "MENTAL_HEALTH_CONCERN",
    "SYSTEM_DEGRADED_PATIENT_UNSERVED",
}

ALERT_TYPE_LABELS_VI: Dict[str, str] = {
    "RED_ZONE_DETECTION": "Phát hiện Vùng Đỏ qua biểu mẫu theo dõi",
    "YELLOW_ZONE_FOLLOWUP_OVERDUE": "Quá hạn 20 phút theo dõi Vùng Vàng",
    "NON_RESPONSE_24H": "Mất liên lạc quá 24 giờ",
    "NON_RESPONSE_12H": "Chưa cập nhật chỉ số sau 12 giờ",
    "CHAT_RED_FLAG_DETECTION": "Phát hiện Cờ Đỏ cấp cứu qua Chatbot",
    "CHAT_YELLOW_ZONE_ALERT": "Cảnh báo Vùng Vàng qua Chatbot",
    "MEDICATION_NONADHERENCE_INTENT": "Ý định tự ý ngưng thuốc (Chatbot)",
    "MENTAL_HEALTH_CONCERN": "Nguy cơ khủng hoảng tâm lý (Chatbot)",
    "SYSTEM_DEGRADED_PATIENT_UNSERVED": "Hệ thống gián đoạn liên tiếp khi phục vụ bệnh nhân",
}

class CarePlanItemDTO(BaseModel):
    id: Optional[str] = None
    item_type: str = Field(..., description="CONTROLLER_MED | RELIEVER_MED | PEF_MEASURE | COMORBIDITY_MED")
    title: str = Field(..., description="Tên thuốc hoặc nhiệm vụ đo")
    dosage: Optional[str] = "2 nhát"
    instructions: Optional[str] = "Hít qua buồng đệm, súc miệng nước sạch"
    schedule_times: List[str] = Field(default_factory=lambda: ["08:00", "20:00"])
    is_active: bool = True

    class Config:
        from_attributes = True

class CarePlanDTO(BaseModel):
    id: str
    patient_id: str
    start_date: date
    end_date: Optional[date] = None
    personal_best_pef: int
    baseline_spo2: int
    action_plan_green: Optional[str] = None
    action_plan_yellow: Optional[str] = None
    action_plan_red: Optional[str] = None
    doctor_notes: Optional[str] = None
    items: List[CarePlanItemDTO] = []

    class Config:
        from_attributes = True

class CarePlanCreateOrUpdateDTO(BaseModel):
    patient_id: str
    personal_best_pef: int = 500
    baseline_spo2: int = 98
    action_plan_green: Optional[str] = None
    action_plan_yellow: Optional[str] = None
    action_plan_red: Optional[str] = None
    doctor_notes: Optional[str] = None
    items: List[CarePlanItemDTO] = []

class CheckinCreateDTO(BaseModel):
    patient_id: str
    pef_value: int
    spo2_value: Optional[int] = 98
    symptoms: Dict[str, Any] = Field(default_factory=dict)
    meds_taken: Dict[str, Any] = Field(default_factory=dict)
    reliever_puffs: int = 0
    notes: Optional[str] = ""

class CheckinResponseDTO(BaseModel):
    checkin_id: str
    action_zone: str
    pef_percent: float
    guidance: str

class CheckinHistoryDTO(BaseModel):
    id: str
    checkin_time: str
    date: str
    pef_value: Optional[int]
    pef_percent: Optional[float]
    spo2_value: Optional[int]
    action_zone: str
    symptoms: Dict[str, Any] = {}
    meds_taken: Dict[str, Any] = {}
    reliever_puffs: int = 0
    notes: Optional[str] = None

class ReminderDTO(BaseModel):
    id: str
    title: str
    message_content: str
    reminder_type: str
    scheduled_time: str
    status: str

    class Config:
        from_attributes = True

class ReminderActionDTO(BaseModel):
    action: str = Field(..., description="ACKNOWLEDGE | SNOOZE")

class NursePatientOverviewDTO(BaseModel):
    patient_id: str
    personal_best_pef: int
    baseline_spo2: int
    doctor_notes: Optional[str]
    adherence_rate_7d: int
    priority_score: int
    has_overdue_reminders: bool
    latest_checkin: Optional[Dict[str, Any]] = None

class AlertTicketDTO(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    checkin_id: Optional[str] = None
    priority: str  # P0_CRITICAL | P1_HIGH | P2_MEDIUM
    alert_type: str
    alert_type_label: Optional[str] = None
    source_channel: Optional[str] = None
    trigger_reason: str
    clinical_data: Dict[str, Any] = Field(default_factory=dict)
    status: str  # OPEN | ACKNOWLEDGED | RESOLVED
    escalation_latency_ms: int = 0
    created_at: str
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    @model_validator(mode="after")
    def _populate_channel_and_label(self) -> "AlertTicketDTO":
        is_chat = (
            self.alert_type in CHAT_ALERT_TYPES
            or (self.clinical_data or {}).get("source") == "CHAT"
        )
        if not self.source_channel:
            self.source_channel = "CHATBOT" if is_chat else "CHECKIN"
        if not self.alert_type_label:
            self.alert_type_label = ALERT_TYPE_LABELS_VI.get(
                self.alert_type, self.alert_type
            )
        return self

    class Config:
        from_attributes = True

class AlertTicketAcknowledgeDTO(BaseModel):
    acknowledged_by: str = Field(default="Điều dưỡng trực ca")

class AlertTicketResolveDTO(BaseModel):
    resolved_by: str = Field(..., description="Tên điều dưỡng / bác sĩ xử lý")
    resolution_notes: str = Field(..., description="Biên bản lâm sàng ghi nhận hành động can thiệp")

class PatientSafetyConfirmDTO(BaseModel):
    patient_id: str
    notes: Optional[str] = "Bệnh nhân xác nhận đã xịt thuốc và nhịp thở ổn định sau 20 phút."

