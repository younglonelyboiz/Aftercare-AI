import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from backend.app.repositories.asthma_repositories import (
    CarePlanRepository,
    CheckinRepository,
    ReminderRepository
)
from backend.app.models.asthma import (
    AsthmaCarePlan,
    AsthmaCarePlanItem,
    AsthmaCheckinLog,
    AsthmaReminder
)
from backend.app.schemas.care_tracker import (
    CarePlanDTO,
    CarePlanCreateOrUpdateDTO,
    CheckinCreateDTO,
    CheckinResponseDTO,
    CheckinHistoryDTO,
    ReminderDTO,
    NursePatientOverviewDTO
)

class AsthmaCareService:
    """Tầng Service chịu trách nhiệm 100% nghiệp vụ lâm sàng, tính toán GINA, Triage."""

    def __init__(
        self,
        care_plan_repo: CarePlanRepository,
        checkin_repo: CheckinRepository,
        reminder_repo: ReminderRepository
    ):
        self.care_plan_repo = care_plan_repo
        self.checkin_repo = checkin_repo
        self.reminder_repo = reminder_repo

    # -------------------------------------------------------------------------
    # 1. CARE PLAN BUSINESS LOGIC
    # -------------------------------------------------------------------------
    def get_care_plan(self, patient_id: str) -> Optional[CarePlanDTO]:
        plan = self.care_plan_repo.get_active_plan_by_patient_id(patient_id)
        if not plan:
            return None
        return CarePlanDTO.model_validate(plan)

    def create_or_update_care_plan(self, data: CarePlanCreateOrUpdateDTO) -> str:
        # Vô hiệu hóa plan cũ nếu có
        self.care_plan_repo.deactivate_existing_plans(data.patient_id)

        new_plan_id = f"plan-{data.patient_id}-{int(datetime.utcnow().timestamp())}"
        
        green_text = data.action_plan_green or f"PEF >= {int(data.personal_best_pef * 0.8)} (>=80%). Duy trì thuốc kiểm soát hàng ngày."
        yellow_text = data.action_plan_yellow or f"PEF {int(data.personal_best_pef * 0.6)} - {int(data.personal_best_pef * 0.8) - 1} (60-80%). Dùng thuốc cắt cơn, nghỉ ngơi."
        red_text = data.action_plan_red or f"PEF < {int(data.personal_best_pef * 0.6)} (<60%). CẤP CỨU NGAY LẬP TỨC 115."

        new_plan = AsthmaCarePlan(
            id=new_plan_id,
            patient_id=data.patient_id,
            start_date=date.today(),
            personal_best_pef=data.personal_best_pef,
            baseline_spo2=data.baseline_spo2,
            action_plan_green=green_text,
            action_plan_yellow=yellow_text,
            action_plan_red=red_text,
            doctor_notes=data.doctor_notes,
            is_active=True
        )

        for it in data.items:
            item_entity = AsthmaCarePlanItem(
                id=f"item-{uuid.uuid4()}",
                care_plan_id=new_plan_id,
                item_type=it.item_type,
                title=it.title,
                dosage=it.dosage,
                instructions=it.instructions,
                schedule_times=it.schedule_times,
                is_active=True
            )
            new_plan.items.append(item_entity)

        self.care_plan_repo.create_care_plan(new_plan)
        return new_plan_id

    # -------------------------------------------------------------------------
    # 2. CHECK-IN & GINA ZONE ENGINE
    # -------------------------------------------------------------------------
    def process_checkin(self, data: CheckinCreateDTO) -> CheckinResponseDTO:
        plan = self.care_plan_repo.get_active_plan_by_patient_id(data.patient_id)
        best_pef = plan.personal_best_pef if plan else 500
        pef_ratio = round((data.pef_value / best_pef) * 100, 1)

        # Thuật toán phân vùng GINA
        has_danger = data.symptoms.get("dangerSign", False)
        has_symptom = any([
            data.symptoms.get("nightWaking", False),
            data.symptoms.get("relieverUsed", False),
            data.symptoms.get("activityLimited", False)
        ])

        if pef_ratio < 60 or (data.spo2_value and data.spo2_value < 92) or has_danger:
            zone = "RED"
            guidance = "🚨 BÁO ĐỘNG ĐỎ CẤP CỨU: Chỉ số của bạn đang ở mức NGUY KỊCH! Xịt ngay 2-4 nhát thuốc cắt cơn qua buồng đệm, ngồi thẳng người và gọi ngay cấp cứu 115 hoặc nhờ người nhà đưa tới bệnh viện!"
        elif pef_ratio < 80 or (data.spo2_value and data.spo2_value < 95) or has_symptom:
            zone = "YELLOW"
            guidance = "⚠️ CẢNH BÁO VÙNG VÀNG: Bạn đang có dấu hiệu hen bùng phát. Hãy xịt ngay thuốc cắt cơn theo đúng hướng dẫn, nghỉ ngơi tại chỗ và theo dõi lại sau 20-30 phút."
        else:
            zone = "GREEN"
            guidance = "🟢 VÙNG XANH AN TOÀN: Kiểm soát hen rất tốt! Hãy tiếp tục duy trì dùng thuốc kiểm soát đúng giờ và lối sống lành mạnh."

        chk_id = f"chk-{uuid.uuid4()}"
        new_log = AsthmaCheckinLog(
            id=chk_id,
            patient_id=data.patient_id,
            checkin_time=datetime.utcnow(),
            pef_value=data.pef_value,
            pef_percent=pef_ratio,
            spo2_value=data.spo2_value,
            action_zone=zone,
            symptoms=data.symptoms,
            meds_taken=data.meds_taken,
            reliever_puffs=data.reliever_puffs,
            notes=data.notes
        )

        self.checkin_repo.create_checkin(new_log)

        return CheckinResponseDTO(
            checkin_id=chk_id,
            action_zone=zone,
            pef_percent=pef_ratio,
            guidance=guidance
        )

    def get_checkin_history(self, patient_id: str, days: int = 30) -> List[CheckinHistoryDTO]:
        logs = self.checkin_repo.get_history_by_patient_id(patient_id, days)
        results = []
        for l in logs:
            results.append(CheckinHistoryDTO(
                id=l.id,
                checkin_time=l.checkin_time.isoformat(),
                date=l.checkin_time.strftime("%Y-%m-%d"),
                pef_value=l.pef_value,
                pef_percent=float(l.pef_percent) if l.pef_percent else None,
                spo2_value=l.spo2_value,
                action_zone=l.action_zone,
                symptoms=l.symptoms or {},
                meds_taken=l.meds_taken or {},
                reliever_puffs=l.reliever_puffs,
                notes=l.notes
            ))
        return results

    # -------------------------------------------------------------------------
    # 3. REMINDER BUSINESS LOGIC
    # -------------------------------------------------------------------------
    def get_active_reminders(self, patient_id: str) -> List[ReminderDTO]:
        reminders = self.reminder_repo.get_active_reminders(patient_id)
        results = []
        for r in reminders:
            results.append(ReminderDTO(
                id=r.id,
                title=r.title,
                message_content=r.message_content,
                reminder_type=r.reminder_type,
                scheduled_time=str(r.scheduled_time),
                status=r.status
            ))
        return results

    def act_on_reminder(self, reminder_id: str, action: str) -> str:
        rem = self.reminder_repo.get_by_id(reminder_id)
        if not rem:
            raise ValueError(f"Không tìm thấy nhắc nhở với ID {reminder_id}")

        if action == "ACKNOWLEDGE":
            self.reminder_repo.update_status(rem, "ACKNOWLEDGED", acknowledged=True)
            return "Đã ghi nhận tuân thủ thuốc thành công!"
        elif action == "SNOOZE":
            self.reminder_repo.update_status(rem, "SNOOZED")
            return "Đã hoãn nhắc nhở thêm 15 phút."
        else:
            raise ValueError("Hành động không hợp lệ (chỉ chấp nhận ACKNOWLEDGE hoặc SNOOZE)")

    # -------------------------------------------------------------------------
    # 4. NURSE TRIAGE & COMMAND CENTER LOGIC
    # -------------------------------------------------------------------------
    def get_nurse_patient_overview(self) -> List[NursePatientOverviewDTO]:
        plans = self.care_plan_repo.get_all_active_plans()
        overview = []

        for p in plans:
            p_id = p.patient_id
            latest = self.checkin_repo.get_latest_checkin(p_id)
            count_7d = self.checkin_repo.count_checkins_in_days(p_id, 7)
            adherence_rate = min(100, int((count_7d / 7) * 100))

            recent_zones = self.checkin_repo.get_recent_zone_counts(p_id, 3)
            has_recent_red = recent_zones.get("RED", 0) > 0
            has_recent_yellow = recent_zones.get("YELLOW", 0) > 0

            overdue_count = self.reminder_repo.count_overdue_reminders(p_id)

            # Thuật toán tính trọng số ưu tiên Triage
            priority_score = 0
            if (latest and latest.action_zone == "RED") or has_recent_red:
                priority_score += 100
            elif (latest and latest.action_zone == "YELLOW") or has_recent_yellow:
                priority_score += 50
            if overdue_count > 0:
                priority_score += 30

            overview.append(NursePatientOverviewDTO(
                patient_id=p_id,
                personal_best_pef=p.personal_best_pef,
                baseline_spo2=p.baseline_spo2,
                doctor_notes=p.doctor_notes,
                adherence_rate_7d=adherence_rate,
                priority_score=priority_score,
                has_overdue_reminders=overdue_count > 0,
                latest_checkin={
                    "time": latest.checkin_time.isoformat() if latest else None,
                    "pef_value": latest.pef_value if latest else None,
                    "pef_percent": float(latest.pef_percent) if latest and latest.pef_percent else None,
                    "spo2": latest.spo2_value if latest else None,
                    "action_zone": latest.action_zone if latest else "UNKNOWN",
                    "reliever_puffs": latest.reliever_puffs if latest else 0
                } if latest else None
            ))

        # Sắp xếp ưu tiên: Priority score cao nhất lên đầu
        overview.sort(key=lambda x: x.priority_score, reverse=True)
        return overview
