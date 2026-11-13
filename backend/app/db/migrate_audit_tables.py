"""
Kịch bản khởi tạo các bảng kiểm toán và hàng đợi leo thang dự phòng (`agent_actions_log`,
`audit_logs`, `escalation_outbox`) — [W07-T5.2, T5.3].
"""
from backend.app.core.database import Base, engine
from backend.app.models.audit import AgentActionLog, AuditLog, EscalationOutbox

AUDIT_TABLES = [
    AgentActionLog.__table__,
    AuditLog.__table__,
    EscalationOutbox.__table__,
]


def migrate_audit_tables(target_engine=None) -> None:
    """Khởi tạo an toàn (idempotent) 3 bảng kiểm toán và hàng đợi outbox."""
    bind_engine = target_engine or engine
    Base.metadata.create_all(bind_engine, tables=AUDIT_TABLES)
    print(
        "Audit & Escalation Outbox tables ready: agent_actions_log, audit_logs, escalation_outbox."
    )


if __name__ == "__main__":
    migrate_audit_tables()

