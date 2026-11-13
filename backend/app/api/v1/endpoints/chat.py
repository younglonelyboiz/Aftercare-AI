import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.repositories.asthma_repositories import AlertTicketRepository
from backend.app.services.escalation_service import EscalationService
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.rag.service import AftercareRAGService
from backend.app.rag.safe_messages import SAFE_FALLBACK_MESSAGE

logger = logging.getLogger("ChatEndpoint")

router = APIRouter()
rag_service = AftercareRAGService()

# [W07-T0.1] Ánh xạ mức rủi ro phát hiện qua chat -> mức ưu tiên & loại vé cảnh báo
CHAT_ESCALATION_POLICY: Dict[str, Dict[str, str]] = {
    "RED_ZONE": {"priority": "P0_CRITICAL", "alert_type": "CHAT_RED_FLAG_DETECTION"},
    "YELLOW_ZONE": {"priority": "P1_HIGH", "alert_type": "CHAT_YELLOW_ZONE_ALERT"},
}
MAX_MESSAGE_EXCERPT = 500


def get_escalation_service(db: Session = Depends(get_db)) -> EscalationService:
    return EscalationService(AlertTicketRepository(db))


async def escalate_chat_result(
    escalation_service: EscalationService,
    patient_id: str,
    message: str,
    result: Dict[str, Any],
    patient_name: Optional[str] = None,
) -> Optional[str]:
    """[W07-T0.1] Tạo/cập nhật AlertTicket khi chat phát hiện Vùng Đỏ/Vàng.

    Không bao giờ ném lỗi ra ngoài: phản hồi hướng dẫn cấp cứu cho bệnh nhân
    phải luôn được trả về kể cả khi tạo vé thất bại (Non-blocking AI).
    Lỗi được ghi log mức CRITICAL để vận hành phát hiện.
    """
    policy = CHAT_ESCALATION_POLICY.get(result.get("safety_status", ""))
    if not policy:
        return None

    screener = result.get("screener") or {}
    reasons = screener.get("matched_reasons") or []
    trigger_reason = (
        "Phát hiện qua Chatbot: " + "; ".join(reasons)
        if reasons
        else f"Phát hiện qua Chatbot: tin nhắn của bệnh nhân khớp quy tắc {result['safety_status']}."
    )
    clinical_data = {
        "source": "CHAT",
        "safety_status": result["safety_status"],
        "matched_flags": screener.get("matched_flags") or [],
        "matched_reasons": reasons,
        "message_excerpt": message[:MAX_MESSAGE_EXCERPT],
    }

    try:
        ticket = await escalation_service.create_or_escalate_ticket(
            patient_id=patient_id,
            priority=policy["priority"],
            alert_type=policy["alert_type"],
            trigger_reason=trigger_reason,
            patient_name=patient_name,
            clinical_data=clinical_data,
        )
        return ticket.id
    except Exception:
        logger.critical(
            "KHÔNG TẠO ĐƯỢC ALERT TICKET %s từ chat cho bệnh nhân %s",
            policy["priority"],
            patient_id,
            exc_info=True,
        )
        return None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    escalation_service: EscalationService = Depends(get_escalation_service),
):
    try:
        # [W07-T0.3] Chạy pipeline đồng bộ (embedding, rerank, LLM) trong threadpool
        # để không chặn event loop -> WebSocket cảnh báo điều dưỡng không bị trễ.
        result = await run_in_threadpool(
            rag_service.process_chat,
            patient_id=request.patient_id,
            message=request.message,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception:
        # [W07-T0.2] Fail-safe: không lộ lỗi kỹ thuật cho bệnh nhân
        logger.exception("Lỗi xử lý chat cho bệnh nhân %s", request.patient_id)
        return ChatResponse(
            response=SAFE_FALLBACK_MESSAGE,
            safety_status="NORMAL",
            citations=[],
            degraded=True,
        )

    # [W07-T0.1] Zero-Silent Failure: Vùng Đỏ/Vàng qua chat phải báo về trạm điều dưỡng
    result["escalation_ticket_id"] = await escalate_chat_result(
        escalation_service,
        patient_id=request.patient_id,
        message=request.message,
        result=result,
    )
    return result
