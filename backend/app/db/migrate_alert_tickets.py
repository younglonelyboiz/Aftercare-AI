"""
Migration script tạo bảng alert_tickets:
- Lưu trữ các ca leo thang cảnh báo y tế (P0_CRITICAL, P1_HIGH, P2_MEDIUM)
- Đảm bảo tính toàn vẹn dữ liệu và hỗ trợ Index truy vấn nhanh cho Nurse Dashboard.
"""
from backend.app.core.database import get_db_connection

CREATE_ALERT_TICKETS_SQL = """
-- Bảng Phiếu cảnh báo leo thang y tế tức thời (Escalation Alert Tickets)
CREATE TABLE IF NOT EXISTS alert_tickets (
    id VARCHAR(100) PRIMARY KEY,
    patient_id VARCHAR(100) NOT NULL,
    checkin_id VARCHAR(100) REFERENCES asthma_checkin_logs(id) ON DELETE SET NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'P0_CRITICAL', -- 'P0_CRITICAL', 'P1_HIGH', 'P2_MEDIUM'
    alert_type VARCHAR(50) NOT NULL, -- 'RED_ZONE_DETECTION', 'YELLOW_ZONE_FOLLOWUP_OVERDUE', 'NON_RESPONSE_24H', 'NON_RESPONSE_12H'
    trigger_reason TEXT NOT NULL,
    clinical_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'
    escalation_latency_ms INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    resolution_notes TEXT
);

-- Chỉ mục tối ưu hóa truy vấn cho trạm trực điều dưỡng
CREATE INDEX IF NOT EXISTS idx_alert_tickets_patient_status ON alert_tickets(patient_id, status);
CREATE INDEX IF NOT EXISTS idx_alert_tickets_status ON alert_tickets(status);
CREATE INDEX IF NOT EXISTS idx_alert_tickets_created_at ON alert_tickets(created_at DESC);
"""

def migrate_alert_tickets():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("Đang khởi tạo bảng 'alert_tickets'...")
            cur.execute(CREATE_ALERT_TICKETS_SQL)
            conn.commit()
            print("✓ Khởi tạo bảng 'alert_tickets' và các Index thành công 100%!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Lỗi khi khởi tạo bảng alert_tickets: {str(e)}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_alert_tickets()

