"""Durable, scoped conversation memory. Notes quote users, not verified clinical facts."""
import re
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import delete, select
from backend.app.core.security import ensure_patient_access
from backend.app.models.identity import Conversation, ChatMessage, MemoryNote

SHORT_TERM_MESSAGES = 12
SHORT_TERM_CHARACTERS = 18000


def conversation_dto(c):
    return {"id": c.id, "patient_id": c.patient_id, "owner_user_id": c.owner_user_id,
            "title": c.title, "summary": c.summary, "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()}


def message_dto(m):
    return {"id": m.id, "sequence": m.sequence, "role": m.role, "content": m.content,
            "safety_status": m.safety_status, "citations": m.citations,
            "created_at": m.created_at.isoformat()}


def get_conversation(db, user, conversation_id, *, write=False, lock=False):
    query = select(Conversation).where(Conversation.id == conversation_id)
    if lock:
        query = query.with_for_update()
    c = db.scalar(query)
    if not c:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
    ensure_patient_access(db, user, c.patient_id)
    if (user.role == "patient" or write) and c.owner_user_id != user.id:
        raise HTTPException(403, "Không được gửi hoặc thay đổi hội thoại của tài khoản khác.")
    return c


def create_conversation(db, user, patient_id):
    from backend.app.services.patient_context import load_profile
    ensure_patient_access(db, user, patient_id)
    try:
        load_profile(patient_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    c = Conversation(patient_id=patient_id, owner_user_id=user.id)
    db.add(c)
    db.flush()
    return c


def build_memory(db, user, conversation, query):
    recent = list(reversed(db.scalars(select(ChatMessage).where(
        ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.sequence.desc()).limit(SHORT_TERM_MESSAGES)).all()))
    history, budget = [], SHORT_TERM_CHARACTERS
    for m in reversed(recent):
        content = m.content[:min(8000, budget)]
        if not content:
            break
        history.insert(0, {"role": m.role, "content": content})
        budget -= len(content)
    notes = db.scalars(select(MemoryNote).where(MemoryNote.patient_id == conversation.patient_id,
        MemoryNote.owner_user_id == user.id).order_by(MemoryNote.created_at.desc()).limit(200)).all()
    recent_ids = {m.id for m in recent}
    words = set(re.findall(r"\w{3,}", query.lower()))
    candidates = [n for n in notes if n.source_message_id not in recent_ids]
    candidates.sort(key=lambda n: (len(words & set(re.findall(r"\w{3,}", n.content.lower()))), n.created_at), reverse=True)
    long_term = [{"text": n.content, "source_message_id": n.source_message_id,
        "conversation_id": n.conversation_id, "reported_at": n.created_at.isoformat(),
        "verification": n.verification} for n in candidates[:6]]
    return history, {"older_turns_summary": conversation.summary[:6000], "long_term_notes": long_term,
                     "last_safety_status": recent[-1].safety_status if recent else None}


def append_exchange(db, conversation, user, query, result):
    sequence = conversation.next_sequence
    user_msg = ChatMessage(conversation_id=conversation.id, sequence=sequence, role="user", content=query)
    assistant_msg = ChatMessage(conversation_id=conversation.id, sequence=sequence + 1, role="assistant",
        content=result["response"], safety_status=result["safety_status"], citations=result.get("citations", []))
    db.add_all([user_msg, assistant_msg])
    db.flush()
    db.add(MemoryNote(patient_id=conversation.patient_id, owner_user_id=user.id,
        conversation_id=conversation.id, source_message_id=user_msg.id, content=query[:1500]))
    if sequence == 1:
        conversation.title = " ".join(query.split())[:100]
    conversation.next_sequence += 2
    conversation.updated_at = datetime.utcnow()
    cutoff = conversation.next_sequence - SHORT_TERM_MESSAGES
    if cutoff > conversation.summary_through:
        older = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation.id,
            ChatMessage.sequence > conversation.summary_through, ChatMessage.sequence < cutoff,
            ChatMessage.role == "user").order_by(ChatMessage.sequence)).all()
        additions = "\n".join(f"[{m.id}; {m.created_at.isoformat()}] Người dùng đã nói: {m.content[:500]}" for m in older)
        conversation.summary = (conversation.summary + "\n" + additions).strip()[-6000:]
        conversation.summary_through = cutoff - 1
    db.commit()
    return user_msg, assistant_msg


def delete_conversation(db, conversation):
    db.execute(delete(MemoryNote).where(MemoryNote.conversation_id == conversation.id))
    db.execute(delete(ChatMessage).where(ChatMessage.conversation_id == conversation.id))
    db.delete(conversation)
    db.commit()
