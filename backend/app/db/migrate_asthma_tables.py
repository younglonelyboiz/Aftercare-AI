"""
Migration script tạo các bảng chuyên biệt cho Hen phế quản:
- asthma_care_plans
- asthma_care_plan_items
- asthma_checkin_logs
- asthma_reminders
Đảm bảo an toàn không ảnh hưởng tới bất kỳ bảng nào sẵn có trong PostgreSQL.
"""
from backend.app.core.database import get_db_connection

CREATE_ASTHMA_TABLES_SQL = """
-- 1. Bảng Kế hoạch chăm sóc Hen phế quản (Asthma Care Plans)
CREATE TABLE IF NOT EXISTS asthma_care_plans (
    id VARCHAR(100) PRIMARY KEY,
    patient_id VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    personal_best_pef INT NOT NULL DEFAULT 500,
    baseline_spo2 INT NOT NULL DEFAULT 98,
    action_plan_green TEXT,
    action_plan_yellow TEXT,
    action_plan_red TEXT,
    doctor_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Hạng mục thuốc và đo lường (Medications & Monitoring Items)
CREATE TABLE IF NOT EXISTS asthma_care_plan_items (
    id VARCHAR(100) PRIMARY KEY,
    care_plan_id VARCHAR(100) NOT NULL REFERENCES asthma_care_plans(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'CONTROLLER_MED', 'RELIEVER_MED', 'PEF_MEASURE', 'COMORBIDITY_MED'
    title VARCHAR(255) NOT NULL,    -- VD: 'Symbicort 160/4.5mcg'
    dosage VARCHAR(100),            -- VD: '2 nhát'
    instructions TEXT,              -- VD: 'Hít qua buồng đệm, súc miệng nước sạch sau khi hít'
    schedule_times JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['07:00', '19:00']
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Nhật ký Check-in hàng ngày của bệnh nhân (Check-in Logs)
CREATE TABLE IF NOT EXISTS asthma_checkin_logs (
    id VARCHAR(100) PRIMARY KEY,
    patient_id VARCHAR(100) NOT NULL,
    checkin_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    pef_value INT,
    pef_percent NUMERIC(5, 2),
    spo2_value INT,
    action_zone VARCHAR(20) NOT NULL, -- 'GREEN', 'YELLOW', 'RED'
    symptoms JSONB DEFAULT '{}'::jsonb,
    meds_taken JSONB DEFAULT '{}'::jsonb,
    reliever_puffs INT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Hàng đợi Nhắc nhở bệnh nhân (Patient Reminders)
CREATE TABLE IF NOT EXISTS asthma_reminders (
    id VARCHAR(100) PRIMARY KEY,
    patient_id VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) REFERENCES asthma_care_plan_items(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    message_content TEXT NOT NULL,
    reminder_type VARCHAR(50) NOT NULL, -- 'MEDICATION', 'PEF_CHECKIN', 'ALERT'
    scheduled_time TIME NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'ACKNOWLEDGED', 'SNOOZED', 'OVERDUE'
    last_triggered_date DATE DEFAULT CURRENT_DATE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asthma_care_plans_patient ON asthma_care_plans(patient_id);
CREATE INDEX IF NOT EXISTS idx_asthma_checkin_patient_time ON asthma_checkin_logs(patient_id, checkin_time DESC);
CREATE INDEX IF NOT EXISTS idx_asthma_reminders_patient_status ON asthma_reminders(patient_id, status);
"""

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("🚀 Đang khởi tạo các bảng Asthma Care-Plan & Checkin...")
            cur.execute(CREATE_ASTHMA_TABLES_SQL)
            conn.commit()
            print("✓ Khởi tạo bảng Asthma thành công 100%!")
    except Exception as e:
        conn.rollback()
        print("❌ Lỗi migration:", e)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
