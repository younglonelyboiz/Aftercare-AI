"""Authentication and durable conversation data, independent of clinical records."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from backend.app.core.database import Base


def new_id():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "auth_users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'nurse', 'patient')"),)
    id = Column(String(32), primary_key=True, default=new_id)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)
    patient_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(32), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NurseAssignment(Base):
    __tablename__ = "nurse_assignments"
    nurse_id = Column(String(32), ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True)
    patient_id = Column(String(100), primary_key=True)


class LoginThrottle(Base):
    __tablename__ = "auth_login_throttles"
    key = Column(String(64), primary_key=True)
    failures = Column(Integer, default=0, nullable=False)
    reset_at = Column(DateTime, nullable=False)


class Conversation(Base):
    __tablename__ = "chat_conversations"
    id = Column(String(32), primary_key=True, default=new_id)
    patient_id = Column(String(100), nullable=False, index=True)
    owner_user_id = Column(String(32), ForeignKey("auth_users.id"), nullable=False, index=True)
    title = Column(String(160), default="Cuộc trò chuyện mới", nullable=False)
    summary = Column(Text, default="", nullable=False)
    summary_through = Column(Integer, default=0, nullable=False)
    next_sequence = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence"),)
    id = Column(String(32), primary_key=True, default=new_id)
    conversation_id = Column(String(32), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    safety_status = Column(String(30), default="NORMAL", nullable=False)
    citations = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MemoryNote(Base):
    __tablename__ = "chat_memory_notes"
    id = Column(String(32), primary_key=True, default=new_id)
    patient_id = Column(String(100), nullable=False, index=True)
    owner_user_id = Column(String(32), ForeignKey("auth_users.id"), nullable=False, index=True)
    conversation_id = Column(String(32), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_message_id = Column(String(32), ForeignKey("chat_messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    verification = Column(String(30), default="user_reported", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
