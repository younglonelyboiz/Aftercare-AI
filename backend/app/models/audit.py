"""
Mô hình cơ sở dữ liệu cho Nhật ký Hành động Agent, Nhật ký Kiểm toán Bất biến (Append-only)
và Hàng đợi Leo thang Dự phòng (Escalation Outbox) — [W07-T5.2, T5.3].

Tuân thủ đặc tả `TongQuanHeThong.md` §4.13–4.14 và `Agent_Orchestration_Guardrails_Design.md` §4.7–4.8:
- `AgentActionLog` (`agent_actions_log`) và `AuditLog` (`audit_logs`) là hai bảng chỉ thêm mới
  (append-only): mọi thao tác UPDATE hoặc DELETE trên hai bảng này đều bị chặn bằng sự kiện ORM.
- Không lưu tin nhắn thô chứa thông tin định danh cá nhân (PII); chỉ lưu mã băm SHA-256
  (`message_sha256`) và bản văn bản đã ẩn danh (`redacted_message`).
- `EscalationOutbox` (`escalation_outbox`) lưu trữ bền vững các yêu cầu tạo vé cảnh báo khi cơ sở dữ liệu
  hoặc dịch vụ leo thang tạm thời gián đoạn để thực hiện gửi lại (retry).
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    event,
)

from backend.app.core.database import Base


def _new_audit_id() -> str:
    return uuid.uuid4().hex


class ImmutableAuditRecordError(RuntimeError):
    """Ngoại lệ ném ra khi có hành vi cố tình sửa hoặc xóa bản ghi kiểm toán append-only."""


class AgentActionLog(Base):
    """Bảng `agent_actions_log`: ghi nhận tổng hợp 1 bản ghi cho mỗi lượt thực thi đồ thị điều phối."""

    __tablename__ = "agent_actions_log"

    id = Column(String(36), primary_key=True, default=_new_audit_id)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    patient_id = Column(String(100), nullable=False, index=True)
    channel = Column(String(20), default="CHAT", nullable=False)
    message_sha256 = Column(String(64), nullable=False)
    redacted_message = Column(Text, nullable=False)
    risk_level = Column(String(30), nullable=False)
    policy_decision = Column(String(20), nullable=True)
    policy_rule_id = Column(String(64), nullable=True)
    evidence_ok = Column(Boolean, default=True, nullable=False)
    output_guard_decision = Column(String(20), nullable=True)
    degraded = Column(Boolean, default=False, nullable=False)
    escalation_ticket_id = Column(String(64), nullable=True)
    latency_ms = Column(JSON, default=dict, nullable=False)
    total_latency_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuditLog(Base):
    """Bảng `audit_logs`: ghi nhận chi tiết từng sự kiện hàng rào an toàn (`GuardEvent`) theo `trace_id`."""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_new_audit_id)
    trace_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    patient_id = Column(String(100), nullable=False, index=True)
    sequence = Column(Integer, default=0, nullable=False)
    node = Column(String(64), nullable=False)
    layer = Column(String(64), nullable=False)
    rule_id = Column(String(64), nullable=False, index=True)
    decision = Column(String(32), nullable=False)
    detail = Column(Text, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class EscalationOutbox(Base):
    """Bảng `escalation_outbox`: hàng đợi bền vững đảm bảo không mất vé cảnh báo khi DB/dịch vụ lỗi tạm thời."""

    __tablename__ = "escalation_outbox"

    id = Column(String(36), primary_key=True, default=_new_audit_id)
    trace_id = Column(String(64), nullable=True, index=True)
    patient_id = Column(String(100), nullable=False, index=True)
    patient_name = Column(String(200), nullable=True)
    priority = Column(String(30), nullable=False)
    alert_type = Column(String(64), nullable=False)
    trigger_reason = Column(Text, nullable=False)
    clinical_data = Column(JSON, default=dict, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    ticket_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def _reject_mutation(mapper, connection, target) -> None:
    raise ImmutableAuditRecordError(
        f"Vi phạm chính sách kiểm toán bất biến (append-only): không được phép sửa hoặc xóa bản ghi {target.__class__.__name__}."
    )


for _audit_model in (AgentActionLog, AuditLog):
    event.listen(_audit_model, "before_update", _reject_mutation)
    event.listen(_audit_model, "before_delete", _reject_mutation)


__all__ = [
    "AgentActionLog",
    "AuditLog",
    "EscalationOutbox",
    "ImmutableAuditRecordError",
]

