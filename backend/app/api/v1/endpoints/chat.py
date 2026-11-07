from threading import Lock
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import current_user, ensure_patient_access
from backend.app.models.identity import User
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_memory import create_conversation, get_conversation, build_memory, append_exchange
from backend.app.services.patient_context import clinical_context

router = APIRouter()
_rag_service = None
_rag_service_lock = Lock()


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        with _rag_service_lock:
            if _rag_service is None:
                from backend.app.rag.service import AftercareRAGService
                _rag_service = AftercareRAGService()
    return _rag_service


@router.post('/chat', response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, user: User = Depends(current_user),
                  db: Session = Depends(get_db), service=Depends(get_rag_service)):
    ensure_patient_access(db, user, request.patient_id)
    if not request.message.strip():
        raise HTTPException(422, 'Tin nhắn không được để trống.')
    try:
        c = (get_conversation(db, user, request.conversation_id, write=True, lock=True)
             if request.conversation_id else create_conversation(db, user, request.patient_id))
        if c.patient_id != request.patient_id:
            raise HTTPException(403, 'Cuộc trò chuyện không thuộc bệnh nhân này.')
        history, memory = build_memory(db, user, c, request.message)
        result = service.process_chat(patient_id=request.patient_id, message=request.message,
            profile=clinical_context(db, request.patient_id), history=history, memory=memory)
        if not result.get('response') or result['response'].startswith('Lỗi'):
            raise HTTPException(503, 'Trợ lý chưa thể trả lời. Vui lòng thử lại; tin nhắn chưa được lưu.')
        _, assistant = append_exchange(db, c, user, request.message, result)
        return {**result, 'conversation_id': c.id, 'message_id': assistant.id}
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(404, str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Không thể xử lý hội thoại lúc này. Vui lòng thử lại.')
