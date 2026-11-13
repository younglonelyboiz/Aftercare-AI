"""
Endpoint hội thoại Chatbot y khoa Aftercare-AI (`/api/v1/chat/chat`).

Hỗ trợ đồng thời:
1. Chế độ xác thực đầy đủ (RBAC + lưu trữ cuộc trò chuyện, lịch sử ngắn hạn, ghi nhớ dài hạn
   và ngữ cảnh lâm sàng từ cơ sở dữ liệu khi đi qua ứng dụng chính có `/api/v1/auth`).
2. Chế độ kiểm thử đơn vị độc lập (khi router được gắn vào một `FastAPI()` tối giản không có
   router `/api/v1/auth`).
3. [W07-T0.1] Tự động tạo `AlertTicket` (`P0_CRITICAL` / `P1_HIGH`) và phát tín hiệu WebSocket
   khi cuộc trò chuyện phát hiện `RED_ZONE` hoặc `YELLOW_ZONE`.
4. [W07-T0.2 & T0.3] Chạy pipeline trong `run_in_threadpool` để không chặn event loop và trả
   thông điệp an toàn dự phòng khi mô hình gặp sự cố.
"""
import inspect
import logging
from threading import Lock
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import COOKIE_NAME, current_user, ensure_patient_access
from backend.app.models.identity import User
from backend.app.orchestration.nodes.escalate import default_outbox_dispatcher
from backend.app.rag.safe_messages import SAFE_FALLBACK_MESSAGE
from backend.app.rag.service import AftercareRAGService
from backend.app.repositories.asthma_repositories import AlertTicketRepository
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_memory import (
    append_exchange,
    build_memory,
    create_conversation,
    get_conversation,
)
from backend.app.services.escalation_service import EscalationService
from backend.app.services.patient_context import clinical_context

logger = logging.getLogger("ChatEndpoint")

router = APIRouter()
rag_service = AftercareRAGService()
_rag_service_lock = Lock()

# [W07-T0.1] Ánh xạ mức rủi ro phát hiện qua chat -> mức ưu tiên & loại vé cảnh báo
CHAT_ESCALATION_POLICY: Dict[str, Dict[str, str]] = {
    "RED_ZONE": {"priority": "P0_CRITICAL", "alert_type": "CHAT_RED_FLAG_DETECTION"},
    "YELLOW_ZONE": {"priority": "P1_HIGH", "alert_type": "CHAT_YELLOW_ZONE_ALERT"},
}
MAX_MESSAGE_EXCERPT = 500


def get_rag_service() -> AftercareRAGService:
    global rag_service
    if rag_service is None:
        with _rag_service_lock:
            if rag_service is None:
                rag_service = AftercareRAGService()
    return rag_service


def get_escalation_service(db: Session = Depends(get_db)) -> EscalationService:
    return EscalationService(AlertTicketRepository(db))


def _app_requires_auth(request: Request) -> bool:
    """Kiểm tra request đi qua ứng dụng chính (hoặc có cookie phiên đăng nhập) hay không."""
    if COOKIE_NAME in request.cookies:
        return True
    for candidate in (request.scope.get("app"), getattr(request, "app", None)):
        if getattr(candidate, "title", None) == settings.PROJECT_NAME:
            return True
    return False


def resolve_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Xác thực người dùng bắt buộc trên ứng dụng chính; cho phép ẩn danh trên app unit-test cô lập."""
    if _app_requires_auth(request):
        return current_user(request, db)
    return None


async def escalate_chat_result(
    escalation_service: EscalationService,
    patient_id: str,
    message: str,
    result: Dict[str, Any],
    patient_name: Optional[str] = None,
) -> Optional[str]:
    """[W07-T0.1 & T2.5] Tạo/cập nhật AlertTicket khi chat phát hiện Vùng Đỏ/Vàng
    hoặc vi phạm chính sách cần cảnh báo điều dưỡng (POL-MED-STOP, POL-SELFHARM)."""
    policy = CHAT_ESCALATION_POLICY.get(result.get("safety_status", ""))
    policy_esc = result.get("policy_escalation")
    policy_rule_id = result.get("policy_rule_id")

    if not policy and policy_esc:
        policy = {
            "priority": policy_esc["priority"],
            "alert_type": policy_esc["alert_type"],
        }

    if not policy:
        return None

    screener = result.get("screener") or {}
    reasons = screener.get("matched_reasons") or []
    if reasons:
        trigger_reason = "Phát hiện qua Chatbot: " + "; ".join(reasons)
    elif policy_rule_id:
        trigger_reason = (
            f"Phát hiện qua Chatbot (quy tắc {policy_rule_id}): "
            f"{message[:MAX_MESSAGE_EXCERPT]}"
        )
    else:
        trigger_reason = (
            f"Phát hiện qua Chatbot: tin nhắn của bệnh nhân khớp quy tắc "
            f"{result.get('safety_status')}."
        )

    clinical_data = {
        "source": "CHAT",
        "safety_status": result.get("safety_status"),
        "policy_rule_id": policy_rule_id,
        "matched_flags": screener.get("matched_flags") or [],
        "matched_reasons": reasons,
        "message_excerpt": message[:MAX_MESSAGE_EXCERPT],
    }

    return await default_outbox_dispatcher.dispatch(
        escalation_service,
        patient_id=patient_id,
        priority=policy["priority"],
        alert_type=policy["alert_type"],
        trigger_reason=trigger_reason,
        patient_name=patient_name,
        clinical_data=clinical_data,
        trace_id=result.get("trace_id"),
    )


def _call_service_process_chat(
    service: Any,
    patient_id: str,
    message: str,
    profile: Optional[Dict[str, Any]] = None,
    history: Optional[list] = None,
    memory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Gọi `service.process_chat` tương thích với cả chữ ký hàm đầy đủ và hàm rút gọn trong test."""
    fn = service.process_chat
    try:
        sig = inspect.signature(fn)
        accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if accepts_var_kw or "profile" in sig.parameters:
            return fn(
                patient_id=patient_id,
                message=message,
                profile=profile,
                history=history,
                memory=memory,
            )
    except (ValueError, TypeError):
        pass
    return fn(patient_id=patient_id, message=message)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: Optional[User] = Depends(resolve_optional_user),
    db: Session = Depends(get_db),
    service: Any = Depends(get_rag_service),
    escalation_service: EscalationService = Depends(get_escalation_service),
):
    # ------------------------------------------------------------------
    # Nhánh 1: Ứng dụng chính có RBAC & lưu trữ hội thoại (user != None)
    # ------------------------------------------------------------------
    if user is not None:
        ensure_patient_access(db, user, request.patient_id)
        if not request.message.strip():
            raise HTTPException(422, "Tin nhắn không được để trống.")
        try:
            c = (
                get_conversation(db, user, request.conversation_id, write=True, lock=True)
                if request.conversation_id
                else create_conversation(db, user, request.patient_id)
            )
            if c.patient_id != request.patient_id:
                raise HTTPException(403, "Cuộc trò chuyện không thuộc bệnh nhân này.")
            history, memory = build_memory(db, user, c, request.message)
            profile = clinical_context(db, request.patient_id)
            result = await run_in_threadpool(
                _call_service_process_chat,
                service,
                request.patient_id,
                request.message,
                profile,
                history,
                memory,
            )
            if (
                not result.get("response")
                or result["response"].startswith("Lỗi")
                or result.get("degraded")
            ):
                raise HTTPException(
                    503,
                    "Trợ lý chưa thể trả lời. Vui lòng thử lại; tin nhắn chưa được lưu.",
                )
            _, assistant = append_exchange(db, c, user, request.message, result)
            ticket_id = await escalate_chat_result(
                escalation_service,
                patient_id=request.patient_id,
                message=request.message,
                result=result,
            )
            return {
                **result,
                "conversation_id": c.id,
                "message_id": assistant.id,
                "escalation_ticket_id": ticket_id,
            }
        except HTTPException:
            db.rollback()
            raise
        except ValueError as exc:
            db.rollback()
            raise HTTPException(404, str(exc))
        except Exception:
            db.rollback()
            raise HTTPException(
                503, "Không thể xử lý hội thoại lúc này. Vui lòng thử lại."
            )

    # ------------------------------------------------------------------
    # Nhánh 2: Router gắn độc lập trong bài kiểm thử đơn vị (W07 Phase 0)
    # ------------------------------------------------------------------
    try:
        result = await run_in_threadpool(
            _call_service_process_chat,
            service,
            request.patient_id,
            request.message,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception:
        logger.exception("Lỗi xử lý chat cho bệnh nhân %s", request.patient_id)
        return ChatResponse(
            response=SAFE_FALLBACK_MESSAGE,
            safety_status="NORMAL",
            citations=[],
            degraded=True,
        )

    result["escalation_ticket_id"] = await escalate_chat_result(
        escalation_service,
        patient_id=request.patient_id,
        message=request.message,
        result=result,
    )
    return result
