"""
Script khởi tạo các bảng quan hệ phục vụ:
1. Care Plans & Items (Phác đồ thuốc & lịch đo)
2. Checkin Logs (Nhật ký chỉ số PEF, SpO2, vùng GINA, thuốc đã dùng)
3. Patient Reminders (Hàng đợi nhắc nhở thuốc & đo lường)
"""

from backend.app.core.database import get_db_connection

CREATE_TABLES_SQL = """
-- 1. Bảng Kế hoạch chăm sóc (Care Plans)
CREATE TABLE IF NOT EXISTS care_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    personal_best_pef INT NOT NULL DEFAULT 500,
    target_spo2 INT NOT NULL DEFAULT 95,
    doctor_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng Hạng mục phác đồ (Thuốc duy trì, đo đạc, tái khám)
CREATE TABLE IF NOT EXISTS care_plan_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    care_plan_id UUID NOT NULL REFERENCES care_plans(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'MEDICATION_CONTROLLER', 'MEDICATION_RELIEVER', 'PEF_MEASURE', 'APPOINTMENT'
    title VARCHAR(255) NOT NULL,    -- 'Xịt Seretide 25/125'
    dosage VARCHAR(100),            -- '2 nhát'
    instructions TEXT,              -- 'Xịt qua buồng đệm, súc miệng nước sạch sau xịt'
    schedule_times JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['08:00', '20:00']
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng Nhật ký Check-in hàng ngày (Checkin Logs)
CREATE TABLE IF NOT EXISTS checkin_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL,
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

-- 4. Bảng Nhắc nhở bệnh nhân (Patient Reminders)
CREATE TABLE IF NOT EXISTS patient_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL,
    care_plan_item_id UUID REFERENCES care_plan_items(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    message_content TEXT NOT NULL,
    reminder_type VARCHAR(50) NOT NULL, -- 'MEDICATION', 'PEF_CHECKIN', 'ALERT'
    scheduled_time TIME NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'ACKNOWLEDGED', 'SNOOZED', 'OVERDUE'
    last_triggered_date DATE DEFAULT CURRENT_DATE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tạo Index tăng tốc truy vấn theo patient_id và thời gian
CREATE INDEX IF NOT EXISTS idx_care_plans_patient ON care_plans(patient_id);
CREATE INDEX IF NOT EXISTS idx_checkin_patient_time ON checkin_logs(patient_id, checkin_time DESC);
CREATE INDEX IF NOT EXISTS idx_reminders_patient_status ON patient_reminders(patient_id, status);
"""

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("🚀 Đang khởi tạo các bảng Care-Plan & Check-in Tracker trong PostgreSQL...")
            cur.execute(CREATE_TABLES_SQL)
            conn.commit()
            print("✓ Khởi tạo bảng thành công!")
    except Exception as e:
        conn.rollback()
        print("❌ Lỗi migration:", e)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
