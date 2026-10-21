from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PatientInfo(BaseModel):
    patient_id: str
    full_name: str
    age: int
    gender: str
    discharge_date: Optional[str] = None

class ClinicalStatus(BaseModel):
    diagnosis: str
    known_triggers: List[str] = []
    personal_best_pef: int
    baseline_spo2: int

class ActionPlanRules(BaseModel):
    green_zone: str
    yellow_zone: str
    red_zone: str

class PatientProfile(BaseModel):
    patient_info: PatientInfo
    clinical_status: ClinicalStatus
    current_medications: Dict[str, str]
    action_plan_rules: ActionPlanRules
    follow_up: Dict[str, str]

class ChatRequest(BaseModel):
    patient_id: str
    message: str

class CitationItem(BaseModel):
    chunk_id: str
    section_title: str
    citation: str
    safety_tier: str
    document_tag: Optional[str] = None
    document_name: Optional[str] = None
    pdf_page: Optional[int] = None
    pdf_url: Optional[str] = None
    snippet: Optional[str] = None
    similarity_score: float

class ChatResponse(BaseModel):
    response: str
    safety_status: str # NORMAL | YELLOW_ZONE | RED_ZONE
    citations: List[CitationItem] = []
