"""
CONTROLLER LAYER (API ROUTER):
- Nhận HTTP Request
- Validate dữ liệu qua Pydantic DTO
- Inject DB Session qua Dependency Injection (get_db)
- Khởi tạo Repository & Service
- Gọi Service và trả về HTTP Response chuẩn
Tuyệt đối không chứa query SQL hoặc logic lâm sàng phức tạp tại đây.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.repositories.asthma_repositories import (
    CarePlanRepository,
    CheckinRepository,
    ReminderRepository
)
from backend.app.services.asthma_care_service import AsthmaCareService
from backend.app.schemas.care_tracker import (
    CarePlanDTO,
    CarePlanCreateOrUpdateDTO,
    CheckinCreateDTO,
    CheckinResponseDTO,
    CheckinHistoryDTO,
    ReminderDTO,
    ReminderActionDTO,
    NursePatientOverviewDTO
)

router = APIRouter()

def get_care_service(db: Session = Depends(get_db)) -> AsthmaCareService:
    """Dependency Provider tạo Service kèm các Repositories tương ứng."""
    care_plan_repo = CarePlanRepository(db)
    checkin_repo = CheckinRepository(db)
    reminder_repo = ReminderRepository(db)
    return AsthmaCareService(care_plan_repo, checkin_repo, reminder_repo)

# -----------------------------------------------------------------------------
# 1. CARE PLANS ENDPOINTS
# -----------------------------------------------------------------------------
@router.get("/care-plans/{patient_id}", response_model=CarePlanDTO)
def get_care_plan(
    patient_id: str,
    service: AsthmaCareService = Depends(get_care_service)
):
    """Lấy phác đồ điều trị và checklist của bệnh nhân."""
    plan = service.get_care_plan(patient_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Chưa có Care Plan cho bệnh nhân này")
    return plan

@router.post("/care-plans/")
def create_or_update_care_plan(
    data: CarePlanCreateOrUpdateDTO,
    service: AsthmaCareService = Depends(get_care_service)
):
    """Điều dưỡng cập nhật phác đồ hoặc Best PEF."""
    plan_id = service.create_or_update_care_plan(data)
    return {"status": "success", "message": "Đã cập nhật Care Plan thành công", "plan_id": plan_id}

# -----------------------------------------------------------------------------
# 2. CHECK-IN ENDPOINTS
# -----------------------------------------------------------------------------
@router.post("/checkin/", response_model=CheckinResponseDTO)
def submit_checkin(
    data: CheckinCreateDTO,
    service: AsthmaCareService = Depends(get_care_service)
):
    """Bệnh nhân nộp số đo PEF & triệu chứng -> Tính toán vùng GINA và chỉ dẫn xử trí."""
    return service.process_checkin(data)

@router.get("/checkin/history/{patient_id}", response_model=List[CheckinHistoryDTO])
def get_checkin_history(
    patient_id: str,
    days: int = Query(default=30, ge=1, le=90),
    service: AsthmaCareService = Depends(get_care_service)
):
    """Lấy lịch sử check-in để hiển thị trên Lịch tháng và vẽ Biểu đồ biến thiên PEF."""
    return service.get_checkin_history(patient_id, days)

# -----------------------------------------------------------------------------
# 3. REMINDERS ENDPOINTS
# -----------------------------------------------------------------------------
@router.get("/reminders/active/{patient_id}", response_model=List[ReminderDTO])
def get_active_reminders(
    patient_id: str,
    service: AsthmaCareService = Depends(get_care_service)
):
    """Lấy danh sách các nhắc nhở thuốc/đo PEF đang chờ thực hiện."""
    return service.get_active_reminders(patient_id)

@router.post("/reminders/{reminder_id}/action")
def act_on_reminder(
    reminder_id: str,
    body: ReminderActionDTO,
    service: AsthmaCareService = Depends(get_care_service)
):
    """Bệnh nhân xác nhận [Đã xịt/uống thuốc] hoặc [Nhắc lại sau 15p]."""
    try:
        msg = service.act_on_reminder(reminder_id, body.action)
        return {"status": "success", "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------------------------------------------------------
# 4. NURSE DASHBOARD ENDPOINTS
# -----------------------------------------------------------------------------
@router.get("/nurse/patients-overview", response_model=List[NursePatientOverviewDTO])
def get_nurse_overview(
    service: AsthmaCareService = Depends(get_care_service)
):
    """Điều dưỡng xem danh sách tất cả bệnh nhân kèm xếp hạng ưu tiên Triage & độ tuân thủ."""
    return service.get_nurse_patient_overview()

# -----------------------------------------------------------------------------
# 5. DEMO RESET ENDPOINT
# -----------------------------------------------------------------------------
@router.post("/reset-demo")
def reset_demo_data():
    """Khôi phục dữ liệu ban đầu cho 3 bệnh nhân mẫu phục vụ demo."""
    try:
        from backend.app.db.seed_asthma_care_plans import seed_asthma_care_plans
        seed_asthma_care_plans()
        return {"status": "success", "message": "Đã reset toàn bộ dữ liệu mẫu (Care Plans, Check-ins, Reminders) cho 3 bệnh nhân thành công!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi reset demo: {str(e)}")

