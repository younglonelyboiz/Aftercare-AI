"""
Script nạp dữ liệu Care Plan & Lịch sử Check-in mẫu (14 ngày qua)
cho 3 bệnh nhân Hen phế quản vào PostgreSQL:
- BN-2026-ASTHMA-01 (Nguyễn Văn An - Hen nhẹ)
- BN-2026-ASTHMA-02 (Trần Thị Mai - Hen nặng, tiền sử ICU)
- BN-2026-ASTHMA-03 (Lê Hoàng Long - Hen trung bình + GERD)
"""
import json
import uuid
from datetime import datetime, timedelta, date, time
from pathlib import Path
from backend.app.core.database import get_db_connection

def seed_asthma_care_plans():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("🌱 Đang seed dữ liệu Care Plans & Check-in cho bệnh nhân Hen phế quản...")
            
            # Xóa sạch dữ liệu mẫu cũ nếu có để tránh trùng
            cur.execute("DELETE FROM asthma_reminders;")
            cur.execute("DELETE FROM asthma_checkin_logs;")
            cur.execute("DELETE FROM asthma_care_plan_items;")
            cur.execute("DELETE FROM asthma_care_plans;")

            # ---------------------------------------------------------
            # BỆNH NHÂN 1: Nguyễn Văn An (Hen nhẹ, kiểm soát tốt)
            # ---------------------------------------------------------
            p1_id = "BN-2026-ASTHMA-01"
            plan1_id = f"plan-{p1_id}"
            cur.execute("""
                INSERT INTO asthma_care_plans 
                (id, patient_id, start_date, personal_best_pef, baseline_spo2, action_plan_green, action_plan_yellow, action_plan_red, doctor_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                plan1_id, p1_id, date.today() - timedelta(days=14), 520, 98,
                "PEF >= 416 (>=80%). Sinh hoạt bình thường, không cần dùng thuốc duy trì hàng ngày.",
                "PEF 312 - 415 (60-80%). Dùng Budesonide/Formoterol 80/4.5mcg xịt 1-2 nhát khi có triệu chứng.",
                "PEF < 312 (<60%). Dùng thuốc cắt cơn ngay, gọi 115 hoặc tới BV Phổi Trung ương.",
                "Bệnh nhân trẻ tuổi, tuân thủ tốt. Hạn chế tiếp xúc phấn hoa và khói bụi."
            ))

            item1_1 = f"item-{uuid.uuid4()}"
            cur.execute("""
                INSERT INTO asthma_care_plan_items 
                (id, care_plan_id, item_type, title, dosage, instructions, schedule_times)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                item1_1, plan1_id, "PEF_MEASURE", "Thổi lưu lượng đỉnh (PEF) buổi sáng", 
                "Thổi 3 lần lấy số lớn nhất", "Thổi lúc mới thức dậy trước khi vận động", json.dumps(["07:00"])
            ))

            # ---------------------------------------------------------
            # BỆNH NHÂN 2: Trần Thị Mai (Hen nặng, nguy cơ cao)
            # ---------------------------------------------------------
            p2_id = "BN-2026-ASTHMA-02"
            plan2_id = f"plan-{p2_id}"
            cur.execute("""
                INSERT INTO asthma_care_plans 
                (id, patient_id, start_date, personal_best_pef, baseline_spo2, action_plan_green, action_plan_yellow, action_plan_red, doctor_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                plan2_id, p2_id, date.today() - timedelta(days=14), 280, 95,
                "PEF >= 224 (>=80%). Duy trì Symbicort 160/4.5 đều đặn sáng/tối.",
                "PEF 168 - 223 (60-80%). Xịt thêm 2 nhát Symbicort hoặc Ventolin, nghỉ ngơi đo lại sau 20 phút.",
                "PEF < 168 (<60%) hoặc khó thở khi nói. CẤP CỨU NGAY! Gọi 115, xịt 4 nhát Ventolin qua buồng đệm.",
                "Bệnh nhân có tiền sử cấp cứu ICU năm ngoái, nhạy cảm với thời tiết lạnh và mạt bụi nhà."
            ))

            item2_1 = f"item-{uuid.uuid4()}"
            cur.execute("""
                INSERT INTO asthma_care_plan_items 
                (id, care_plan_id, item_type, title, dosage, instructions, schedule_times)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                item2_1, plan2_id, "CONTROLLER_MED", "Xịt Symbicort 160/4.5mcg", 
                "2 nhát/lần", "Hít sâu qua buồng đệm, nín thở 10s, súc miệng nước ấm sạch", json.dumps(["08:00", "20:00"])
            ))

            item2_2 = f"item-{uuid.uuid4()}"
            cur.execute("""
                INSERT INTO asthma_care_plan_items 
                (id, care_plan_id, item_type, title, dosage, instructions, schedule_times)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                item2_2, plan2_id, "PEF_MEASURE", "Đo lưu lượng đỉnh (PEF) 2 lần/ngày", 
                "Thổi 3 lần", "Đo vào lúc 07:30 sáng và 19:30 tối trước khi xịt thuốc", json.dumps(["07:30", "19:30"])
            ))

            # ---------------------------------------------------------
            # BỆNH NHÂN 3: Lê Hoàng Long (Hen trung bình + GERD)
            # ---------------------------------------------------------
            p3_id = "BN-2026-ASTHMA-03"
            plan3_id = f"plan-{p3_id}"
            cur.execute("""
                INSERT INTO asthma_care_plans 
                (id, patient_id, start_date, personal_best_pef, baseline_spo2, action_plan_green, action_plan_yellow, action_plan_red, doctor_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                plan3_id, p3_id, date.today() - timedelta(days=14), 400, 97,
                "PEF >= 320 (>=80%). Duy trì Fluticasone/Salmeterol 250mcg đều đặn.",
                "PEF 240 - 319 (60-80%). Xịt Salbutamol 100mcg khi có rít thở hoặc ho về đêm.",
                "PEF < 240 (<60%). Báo ngay cho Bệnh viện ĐHYD TP.HCM hoặc gọi 115.",
                "Có trào ngược dạ dày thực quản (GERD), uống Esomeprazole trước ăn sáng, không ăn sát giờ ngủ."
            ))

            item3_1 = f"item-{uuid.uuid4()}"
            cur.execute("""
                INSERT INTO asthma_care_plan_items 
                (id, care_plan_id, item_type, title, dosage, instructions, schedule_times)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                item3_1, plan3_id, "CONTROLLER_MED", "Fluticasone/Salmeterol 250mcg", 
                "1 nhát/lần", "Hít sâu giữ hơi, súc miệng sau khi dùng", json.dumps(["08:00", "20:00"])
            ))

            item3_2 = f"item-{uuid.uuid4()}"
            cur.execute("""
                INSERT INTO asthma_care_plan_items 
                (id, care_plan_id, item_type, title, dosage, instructions, schedule_times)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                item3_2, plan3_id, "COMORBIDITY_MED", "Esomeprazole 40mg (GERD)", 
                "1 viên", "Uống trước bữa ăn sáng 30 phút", json.dumps(["07:00"])
            ))

            # ---------------------------------------------------------
            # SEED LỊCH SỬ CHECK-IN 10 NGÀY QUA CHO BỆNH NHÂN 2 (CÓ NGÀY VÀNG, NGÀY ĐỎ)
            # ---------------------------------------------------------
            checkins_data = [
                (10, 270, 96, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Cảm thấy khỏe, không ho"),
                (9, 275, 96, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Hít thở bình thường"),
                (8, 260, 95, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Hơi lạnh cổ họng"),
                (7, 210, 93, "YELLOW", {"nightWaking": True, "relieverUsed": True}, {"symbicort_morning": True, "symbicort_evening": True}, 2, "Thức giấc lúc 3h sáng vì ho và rít, xịt 2 nhát Ventolin đỡ dần"),
                (6, 220, 94, "YELLOW", {"activityLimited": True}, {"symbicort_morning": True, "symbicort_evening": True}, 1, "Đi bộ lên cầu thang thấy hụt hơi nhẹ"),
                (5, 265, 96, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Bớt ho"),
                (4, 270, 95, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Ổn định"),
                (3, 160, 91, "RED", {"dangerSign": True, "nightWaking": True, "relieverUsed": True}, {"symbicort_morning": True}, 4, "Lên cơn hen lúc nửa đêm, co rút hõm ức, khó thở khi nói. Đã gọi cấp cứu."),
                (2, 215, 93, "YELLOW", {"activityLimited": True}, {"symbicort_morning": True, "symbicort_evening": True}, 2, "Đang hồi phục sau cơn cấp, còn mệt"),
                (1, 250, 95, "GREEN", {}, {"symbicort_morning": True, "symbicort_evening": True}, 0, "Hôm qua ổn định hơn, đỡ rít"),
            ]

            for days_ago, pef_val, spo2_val, zone, symptoms, meds, relievers, note in checkins_data:
                check_time = datetime.now() - timedelta(days=days_ago, hours=3)
                p2_best = 280
                pef_pct = round((pef_val / p2_best) * 100, 1)
                cur.execute("""
                    INSERT INTO asthma_checkin_logs 
                    (id, patient_id, checkin_time, pef_value, pef_percent, spo2_value, action_zone, symptoms, meds_taken, reliever_puffs, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    f"chk-{uuid.uuid4()}", p2_id, check_time, pef_val, pef_pct, spo2_val, zone,
                    json.dumps(symptoms), json.dumps(meds), relievers, note
                ))

            # Seed check-in cho bệnh nhân 1 (đều đặn Xanh)
            for d in range(1, 8):
                cur.execute("""
                    INSERT INTO asthma_checkin_logs 
                    (id, patient_id, checkin_time, pef_value, pef_percent, spo2_value, action_zone, symptoms, meds_taken, reliever_puffs, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    f"chk-{uuid.uuid4()}", p1_id, datetime.now() - timedelta(days=d, hours=2),
                    500 + (d * 3), round(((500 + d*3)/520)*100, 1), 98, "GREEN",
                    json.dumps({}), json.dumps({"morning_pef": True}), 0, "Khỏe mạnh bình thường"
                ))

            # ---------------------------------------------------------
            # SEED REMINDERS HÔM NAY CHO BỆNH NHÂN 2
            # ---------------------------------------------------------
            cur.execute("""
                INSERT INTO asthma_reminders
                (id, patient_id, item_id, title, message_content, reminder_type, scheduled_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                f"rem-{uuid.uuid4()}", p2_id, item2_1, "Nhắc xịt thuốc kiểm soát tối",
                "Đã 20:00, bác nhớ xịt 2 nhát Symbicort 160/4.5mcg qua buồng đệm và súc miệng nước ấm nhé!",
                "MEDICATION", time(20, 0), "PENDING"
            ))

            cur.execute("""
                INSERT INTO asthma_reminders
                (id, patient_id, item_id, title, message_content, reminder_type, scheduled_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                f"rem-{uuid.uuid4()}", p2_id, item2_2, "Nhắc đo PEF buổi tối",
                "Bác hãy đo PEF 3 lần và ghi lại số cao nhất trước khi xịt thuốc.",
                "PEF_CHECKIN", time(19, 30), "OVERDUE"
            ))

            conn.commit()
            print("✓ Seed dữ liệu Care Plans & Checkin cho 3 bệnh nhân Hen phế quản thành công 100%!")
    except Exception as e:
        conn.rollback()
        print("❌ Lỗi khi seed:", e)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    seed_asthma_care_plans()
