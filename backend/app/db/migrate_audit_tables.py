"""
Kịch bản khởi tạo các bảng kiểm toán và hàng đợi leo thang dự phòng (`system_audit_logs`,
`agent_actions_log`, `audit_logs`, `escalation_outbox`) — [W07-T5.2, T5.3, AUD-3].
"""
from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.models.audit import (
    AgentActionLog,
    AuditLog,
    EscalationOutbox,
    SystemAuditLog,
)

AUDIT_TABLES = [
    SystemAuditLog.__table__,
    AgentActionLog.__table__,
    AuditLog.__table__,
    EscalationOutbox.__table__,
]


def migrate_audit_tables(target_engine=None) -> None:
    """Khởi tạo an toàn (idempotent) 4 bảng kiểm toán và hàng đợi outbox."""
    bind_engine = target_engine or engine
    Base.metadata.create_all(bind_engine, tables=AUDIT_TABLES)
    if bind_engine.dialect.name == "postgresql":
        with bind_engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE system_audit_logs ADD COLUMN IF NOT EXISTS chain_seq INTEGER NOT NULL DEFAULT 1"
                )
            )
    print(
        "Audit & Escalation Outbox tables ready: system_audit_logs, agent_actions_log, audit_logs, escalation_outbox."
    )


if __name__ == "__main__":
    migrate_audit_tables()
