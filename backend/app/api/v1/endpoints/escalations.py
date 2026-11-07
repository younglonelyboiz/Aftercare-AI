import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.app.core.database import get_db, SessionLocal
from backend.app.core.config import settings
from backend.app.core.security import COOKIE_NAME, current_user, staff_user, patient_scope, session_user, allowed_patient_ids, ensure_patient_access
from backend.app.models.identity import User
from backend.app.core.websocket_manager import nurse_ws_manager
from backend.app.repositories.asthma_repositories import AlertTicketRepository
from backend.app.services.escalation_service import EscalationService
from backend.app.schemas.care_tracker import (
    AlertTicketDTO,
    AlertTicketAcknowledgeDTO,
    AlertTicketResolveDTO,
    PatientSafetyConfirmDTO
)
from backend.app.workers.non_response_worker import non_response_worker

logger = logging.getLogger("EscalationEndpoints")
router = APIRouter()

def get_escalation_service(db: Session = Depends(get_db)) -> EscalationService:
    ticket_repo = AlertTicketRepository(db)
    return EscalationService(ticket_repo)

# -----------------------------------------------------------------------------
# 1. WEBSOCKET REAL-TIME NURSE ALERTS
# -----------------------------------------------------------------------------
@router.websocket("/ws/nurse-alerts")
async def nurse_alerts_websocket(websocket: WebSocket):
    """Kênh WebSocket thời gian thực truyền phát cảnh báo cấp cứu tới Nurse Station."""
    if websocket.headers.get("origin") not in settings.CORS_ORIGINS:
        await websocket.close(code=1008)
        return
    raw_token = websocket.cookies.get(COOKIE_NAME)
    with SessionLocal() as db:
        user = session_user(db, raw_token)
        if not user or user.role not in {"admin", "nurse"}:
            await websocket.close(code=1008)
            return
    await nurse_ws_manager.connect(websocket, raw_token)
    try:
        # Gửi thông điệp chào mừng & xác nhận kết nối thành công
        await websocket.send_json({
            "event": "CONNECTED",
            "message": "Đã kết nối thành công tới Trung tâm Cảnh báo Điều dưỡng Aftercare-AI (Nurse Alert Hub)."
        })

        while True:
            data = await websocket.receive_text()
            with SessionLocal() as db:
                user = session_user(db, raw_token)
                if not user or user.role not in {"admin", "nurse"}:
                    await websocket.close(code=1008)
                    nurse_ws_manager.disconnect(websocket)
                    return
            # Xử lý heartbeat ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            else:
                logger.debug(f"Nhận tin từ Nurse Client: {data}")
    except WebSocketDisconnect:
        nurse_ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Lỗi WebSocket trạm trực: {str(e)}")
        nurse_ws_manager.disconnect(websocket)

# -----------------------------------------------------------------------------
# 2. REST API: LẤY DANH SÁCH VÉ CẢNH BÁO
# -----------------------------------------------------------------------------
@router.get("/tickets/active", response_model=List[AlertTicketDTO])
def get_active_tickets(service: EscalationService = Depends(get_escalation_service), user: User = Depends(staff_user)):
    """Lấy danh sách các vé cảnh báo đang chờ xử lý (OPEN hoặc ACKNOWLEDGED)."""
    allowed = allowed_patient_ids(service.ticket_repo.db, user)
    return service.get_active_tickets(patient_ids=allowed)

@router.get("/tickets/history", response_model=List[AlertTicketDTO])
def get_recent_tickets(service: EscalationService = Depends(get_escalation_service), user: User = Depends(staff_user)):
    """Lấy lịch sử 50 vé cảnh báo gần nhất kể cả đã giải quyết."""
    allowed = allowed_patient_ids(service.ticket_repo.db, user)
    return service.get_recent_tickets(limit=50, patient_ids=allowed)

# -----------------------------------------------------------------------------
# 3. REST API: TIẾP NHẬN & GIẢI QUYẾT VÉ CẢNH BÁO (AUDIT TRAIL)
# -----------------------------------------------------------------------------
@router.post("/tickets/{ticket_id}/acknowledge", response_model=AlertTicketDTO)
async def acknowledge_ticket(
    ticket_id: str,
    body: AlertTicketAcknowledgeDTO,
    user: User = Depends(staff_user),
    service: EscalationService = Depends(get_escalation_service)
):
    """Điều dưỡng bấm 'Tiếp nhận ca' -> Tắt còi báo động âm thanh và cập nhật trạng thái."""
    entity = service.ticket_repo.get_by_id(ticket_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy vé cảnh báo.")
    ensure_patient_access(service.ticket_repo.db, user, entity.patient_id)
    ticket = await service.acknowledge_ticket(ticket_id, user.full_name)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy vé cảnh báo với ID này.")
    return ticket

@router.post("/tickets/{ticket_id}/resolve", response_model=AlertTicketDTO)
async def resolve_ticket(
    ticket_id: str,
    body: AlertTicketResolveDTO,
    user: User = Depends(staff_user),
    service: EscalationService = Depends(get_escalation_service)
):
    """Điều dưỡng nhập biên bản can thiệp lâm sàng và đóng vé cảnh báo."""
    if not body.resolution_notes or len(body.resolution_notes.strip()) < 5:
        raise HTTPException(status_code=400, detail="Vui lòng nhập biên bản can thiệp lâm sàng đầy đủ trước khi đóng ca.")
    entity = service.ticket_repo.get_by_id(ticket_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy vé cảnh báo.")
    ensure_patient_access(service.ticket_repo.db, user, entity.patient_id)
    ticket = await service.resolve_ticket(ticket_id, user.full_name, body.resolution_notes)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy vé cảnh báo với ID này.")
    return ticket

# -----------------------------------------------------------------------------
# 4. REST API: BỆNH NHÂN XÁC NHẬN AN TOÀN SAU 20 PHÚT VÙNG VÀNG
# -----------------------------------------------------------------------------
@router.post("/patients/{patient_id}/safety-confirm-20m", dependencies=[Depends(patient_scope)])
async def patient_safety_confirm(
    patient_id: str,
    body: PatientSafetyConfirmDTO,
    service: EscalationService = Depends(get_escalation_service)
):
    """Bệnh nhân xác nhận đã xịt thuốc cắt cơn và nhịp thở ổn định sau 20 phút Vùng Vàng."""
    if body.patient_id != patient_id:
        raise HTTPException(422, "Mã bệnh nhân không khớp.")
    return await service.confirm_patient_safety_20m(patient_id, body.notes or "Bệnh nhân báo an toàn.")

# -----------------------------------------------------------------------------
# 5. REST API: KÍCH HOẠT QUÉT THỦ CÔNG NON-RESPONSE (TEST & DEMO)
# -----------------------------------------------------------------------------
@router.post("/scan-non-response")
async def trigger_manual_scan(user: User = Depends(staff_user), db: Session = Depends(get_db)):
    """Kích hoạt quét tức thì để kiểm thử phát hiện 24h mất liên lạc hoặc 20m Vùng Vàng."""
    stats = await non_response_worker.scan_once(patient_ids=allowed_patient_ids(db, user))
    return {"status": "success", "scan_results": stats}

