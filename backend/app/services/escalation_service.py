import time
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models.asthma import AlertTicket
from backend.app.repositories.asthma_repositories import AlertTicketRepository
from backend.app.schemas.care_tracker import AlertTicketDTO
from backend.app.core.websocket_manager import nurse_ws_manager

logger = logging.getLogger("EscalationService")

class EscalationService:
    """Service chịu trách nhiệm xử lý nghiệp vụ leo thang cảnh báo y tế (Escalation Pipeline)."""

    def __init__(self, ticket_repo: AlertTicketRepository):
        self.ticket_repo = ticket_repo

    async def create_or_escalate_ticket(
        self,
        patient_id: str,
        priority: str, # P0_CRITICAL | P1_HIGH | P2_MEDIUM
        alert_type: str, # RED_ZONE_DETECTION | YELLOW_ZONE_FOLLOWUP_OVERDUE | NON_RESPONSE_24H | NON_RESPONSE_12H
        trigger_reason: str,
        patient_name: Optional[str] = None,
        checkin_id: Optional[str] = None,
        clinical_data: Optional[Dict[str, Any]] = None
    ) -> AlertTicketDTO:
        start_time = time.perf_counter()

        # 1. Debounce / De-duplication: Kiểm tra vé cùng loại đang OPEN trong 5 phút qua
        existing = self.ticket_repo.find_recent_open_ticket(
            patient_id=patient_id,
            alert_type=alert_type,
            window_minutes=5
        )

        if existing:
            # Cập nhật vé sẵn có thay vì tạo vé rác
            existing.trigger_reason = trigger_reason
            if clinical_data:
                existing.clinical_data = clinical_data
            self.ticket_repo.db.commit()
            self.ticket_repo.db.refresh(existing)
            ticket_entity = existing
            logger.info(f"Đã debounce và cập nhật vé sẵn có: {existing.id} cho {patient_id}")
        else:
            # 2. Tạo vé mới
            ticket_entity = AlertTicket(
                id=f"ticket-{uuid.uuid4().hex[:12]}",
                patient_id=patient_id,
                checkin_id=checkin_id,
                priority=priority,
                alert_type=alert_type,
                trigger_reason=trigger_reason,
                clinical_data=clinical_data or {},
                status="OPEN",
                created_at=datetime.utcnow()
            )
            self.ticket_repo.create_ticket(ticket_entity)
            logger.warning(f"🚨 TẠO MỚI ALERT TICKET [{priority}]: {ticket_entity.id} - Bệnh nhân: {patient_id} - Lý do: {trigger_reason}")

        # 3. Tính toán độ trễ leo thang (Escalation Latency tính bằng ms)
        end_time = time.perf_counter()
        latency_ms = max(1, int((end_time - start_time) * 1000))
        ticket_entity.escalation_latency_ms = latency_ms

        dto = self._map_to_dto(ticket_entity, patient_name)

        # 4. Phát tín hiệu thời gian thực qua WebSocket tới Nurse Station
        await nurse_ws_manager.broadcast_json({
            "event": "NEW_ALERT_TICKET",
            "ticket": dto.model_dump()
        })

        return dto

    def get_active_tickets(self, patient_ids=None) -> List[AlertTicketDTO]:
        tickets = self.ticket_repo.get_active_tickets(patient_ids=patient_ids)
        return [self._map_to_dto(t) for t in tickets]

    def get_recent_tickets(self, limit: int = 50, patient_ids=None) -> List[AlertTicketDTO]:
        tickets = self.ticket_repo.get_recent_tickets(limit=limit, patient_ids=patient_ids)
        return [self._map_to_dto(t) for t in tickets]

    async def acknowledge_ticket(self, ticket_id: str, acknowledged_by: str) -> Optional[AlertTicketDTO]:
        ticket = self.ticket_repo.acknowledge_ticket(ticket_id, acknowledged_by)
        if not ticket:
            return None
        dto = self._map_to_dto(ticket)
        await nurse_ws_manager.broadcast_json({
            "event": "TICKET_ACKNOWLEDGED",
            "ticket": dto.model_dump()
        })
        return dto

    async def resolve_ticket(self, ticket_id: str, resolved_by: str, resolution_notes: str) -> Optional[AlertTicketDTO]:
        ticket = self.ticket_repo.resolve_ticket(ticket_id, resolved_by, resolution_notes)
        if not ticket:
            return None
        dto = self._map_to_dto(ticket)
        await nurse_ws_manager.broadcast_json({
            "event": "TICKET_RESOLVED",
            "ticket": dto.model_dump()
        })
        return dto

    async def confirm_patient_safety_20m(self, patient_id: str, notes: str) -> Dict[str, Any]:
        """Bệnh nhân bấm nút xác nhận đã xịt thuốc và an toàn sau 20 phút."""
        self.ticket_repo.resolve_open_tickets_by_patient(
            patient_id=patient_id,
            alert_types=["YELLOW_ZONE_FOLLOWUP_OVERDUE", "YELLOW_ZONE_ALERT"],
            notes=notes
        )
        await nurse_ws_manager.broadcast_json({
            "event": "PATIENT_CONFIRMED_SAFE",
            "patient_id": patient_id,
            "message": notes
        })
        return {"status": "success", "message": "Đã ghi nhận an toàn và đóng các cảnh báo Vùng Vàng tương ứng."}

    def _map_to_dto(self, ticket: AlertTicket, patient_name: Optional[str] = None) -> AlertTicketDTO:
        # Nếu chưa có tên, ánh xạ tên mặc định theo mã bệnh nhân mẫu
        name_map = {
            "BN-2026-ASTHMA-01": "Nguyễn Văn An (28t)",
            "BN-2026-ASTHMA-02": "Trần Thị Mai (61t)",
            "BN-2026-ASTHMA-03": "Lê Hoàng Long (45t)"
        }
        resolved_name = patient_name or name_map.get(ticket.patient_id, ticket.patient_id)

        return AlertTicketDTO(
            id=ticket.id,
            patient_id=ticket.patient_id,
            patient_name=resolved_name,
            checkin_id=ticket.checkin_id,
            priority=ticket.priority,
            alert_type=ticket.alert_type,
            trigger_reason=ticket.trigger_reason,
            clinical_data=ticket.clinical_data or {},
            status=ticket.status,
            escalation_latency_ms=ticket.escalation_latency_ms or 0,
            created_at=ticket.created_at.isoformat() if ticket.created_at else datetime.utcnow().isoformat(),
            acknowledged_at=ticket.acknowledged_at.isoformat() if ticket.acknowledged_at else None,
            acknowledged_by=ticket.acknowledged_by,
            resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            resolved_by=ticket.resolved_by,
            resolution_notes=ticket.resolution_notes
        )

