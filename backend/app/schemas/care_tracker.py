from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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
