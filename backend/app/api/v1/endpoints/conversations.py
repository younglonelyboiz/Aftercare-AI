from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import current_user, ensure_patient_access
from backend.app.models.identity import Conversation, ChatMessage, MemoryNote, User
from backend.app.services.chat_memory import (conversation_dto, create_conversation, delete_conversation,
    get_conversation, message_dto)

router = APIRouter()


class ConversationCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=100)


@router.get("/conversations")
def list_conversations(patient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_patient_access(db, user, patient_id)
    return [conversation_dto(c) for c in db.scalars(select(Conversation).where(
        Conversation.patient_id == patient_id, Conversation.owner_user_id == user.id
    ).order_by(Conversation.updated_at.desc()).limit(100)).all()]


@router.post("/conversations", status_code=201)
def new_conversation(body: ConversationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = create_conversation(db, user, body.patient_id)
    db.commit()
    return conversation_dto(c)


@router.get("/conversations/{conversation_id}")
def read_conversation(conversation_id: str, before: int | None = Query(default=None, ge=1),
                      user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_conversation(db, user, conversation_id)
    query = select(ChatMessage).where(ChatMessage.conversation_id == c.id)
    if before is not None:
        query = query.where(ChatMessage.sequence < before)
    rows = list(reversed(db.scalars(query.order_by(ChatMessage.sequence.desc()).limit(100)).all()))
    return {**conversation_dto(c), "messages": [message_dto(m) for m in rows],
            "has_older": bool(rows and rows[0].sequence > 1)}


@router.delete("/conversations/{conversation_id}", status_code=204)
def remove_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_conversation(db, user, conversation_id, write=True, lock=True)
    delete_conversation(db, c)


@router.get("/memory")
def list_memory(patient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_patient_access(db, user, patient_id)
    notes = db.scalars(select(MemoryNote).where(MemoryNote.patient_id == patient_id,
        MemoryNote.owner_user_id == user.id).order_by(MemoryNote.created_at.desc()).limit(100)).all()
    return [{"id": n.id, "content": n.content, "source_message_id": n.source_message_id,
             "conversation_id": n.conversation_id, "verification": n.verification,
             "created_at": n.created_at.isoformat()} for n in notes]


@router.delete("/memory/{note_id}", status_code=204)
def forget_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    note = db.get(MemoryNote, note_id)
    if not note:
        raise HTTPException(404, "Không tìm thấy ghi nhớ.")
    ensure_patient_access(db, user, note.patient_id)
    if note.owner_user_id != user.id:
        raise HTTPException(403, "Không được xóa ghi nhớ của tài khoản khác.")
    db.delete(note)
    db.commit()
