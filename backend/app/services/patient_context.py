"""Shared, current patient context; clinical DB values supersede the static seed profile."""
import copy
import json
from pathlib import Path
from sqlalchemy import select
from backend.app.models.asthma import AsthmaCarePlan, AsthmaCheckinLog, AlertTicket

PROFILES_DIR = Path(__file__).resolve().parents[3] / "Data" / "patient_profiles"


def load_profile(patient_id: str):
    for file in PROFILES_DIR.glob("*.json"):
        data = json.loads(file.read_text(encoding="utf-8"))
        if data.get("patient_info", {}).get("patient_id") == patient_id:
            return data
    raise ValueError(f"Không tìm thấy hồ sơ cho bệnh nhân có mã: {patient_id}")


def clinical_context(db, patient_id: str):
    profile = copy.deepcopy(load_profile(patient_id))
    plan = db.scalar(select(AsthmaCarePlan).where(AsthmaCarePlan.patient_id == patient_id,
                     AsthmaCarePlan.is_active.is_(True)).order_by(AsthmaCarePlan.created_at.desc()).limit(1))
    if plan:
        profile.setdefault("clinical_status", {}).update(personal_best_pef=plan.personal_best_pef, baseline_spo2=plan.baseline_spo2)
        rules = profile.setdefault("action_plan_rules", {})
        for zone in ("green", "yellow", "red"):
            value = getattr(plan, f"action_plan_{zone}")
            rules[f"{zone}_zone"] = value or "Kế hoạch hiện hành chưa có chỉ dẫn cho vùng này; cần xác nhận với đội ngũ chăm sóc."
        profile["active_care_plan"] = {"doctor_notes": plan.doctor_notes, "updated_at": plan.updated_at.isoformat(),
            "items": [{"title": i.title, "type": i.item_type, "dosage": i.dosage,
                       "instructions": i.instructions, "schedule_times": i.schedule_times} for i in plan.items if i.is_active]}
        # An existing plan is authoritative, including an empty medication list.
        controllers = [i for i in plan.items if i.is_active and i.item_type == "CONTROLLER_MED"]
        relievers = [i for i in plan.items if i.is_active and i.item_type == "RELIEVER_MED"]
        profile["current_medications"] = {
            "controller_med": "; ".join(f"{i.title}: {i.dosage or ''}" for i in controllers) or "Không có thuốc duy trì trong kế hoạch hiện hành.",
            "reliever_med": "; ".join(f"{i.title}: {i.dosage or ''}" for i in relievers) or "Thuốc cắt cơn theo đơn đã được nhân viên y tế xác nhận (kế hoạch hiện hành chưa ghi thuốc cụ thể)."
        }
    latest = db.scalar(select(AsthmaCheckinLog).where(AsthmaCheckinLog.patient_id == patient_id).order_by(AsthmaCheckinLog.checkin_time.desc()).limit(1))
    if latest:
        profile["latest_checkin"] = {"time": latest.checkin_time.isoformat(), "pef": latest.pef_value,
            "spo2": latest.spo2_value, "zone": latest.action_zone, "symptoms": latest.symptoms,
            "notes": latest.notes, "reliever_puffs": latest.reliever_puffs}
    tickets = db.scalars(select(AlertTicket).where(AlertTicket.patient_id == patient_id,
        AlertTicket.status.in_(["OPEN", "ACKNOWLEDGED"])).order_by(AlertTicket.created_at.desc()).limit(5)).all()
    profile["active_alerts"] = [{"priority": t.priority, "type": t.alert_type, "status": t.status,
                                "reason": t.trigger_reason, "time": t.created_at.isoformat()} for t in tickets]
    return profile
