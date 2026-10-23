import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, desc

from backend.app.models.asthma import (
    AsthmaCarePlan, 
    AsthmaCarePlanItem, 
    AsthmaCheckinLog, 
    AsthmaReminder
)

class CarePlanRepository:
    """Tầng Repository chuyên trách truy vấn Care Plans & Items."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_plan_by_patient_id(self, patient_id: str) -> Optional[AsthmaCarePlan]:
        stmt = (
            select(AsthmaCarePlan)
            .where(AsthmaCarePlan.patient_id == patient_id, AsthmaCarePlan.is_active == True)
            .order_by(desc(AsthmaCarePlan.created_at))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def get_all_active_plans(self) -> List[AsthmaCarePlan]:
        stmt = select(AsthmaCarePlan).where(AsthmaCarePlan.is_active == True)
        return list(self.db.scalars(stmt).all())

    def deactivate_existing_plans(self, patient_id: str):
        stmt = (
            update(AsthmaCarePlan)
            .where(AsthmaCarePlan.patient_id == patient_id)
            .values(is_active=False)
        )
        self.db.execute(stmt)
        self.db.commit()

    def create_care_plan(self, plan: AsthmaCarePlan) -> AsthmaCarePlan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

class CheckinRepository:
    """Tầng Repository chuyên trách truy vấn Checkin Logs."""

    def __init__(self, db: Session):
        self.db = db

    def create_checkin(self, checkin: AsthmaCheckinLog) -> AsthmaCheckinLog:
        self.db.add(checkin)
        self.db.commit()
        self.db.refresh(checkin)
        return checkin

    def get_history_by_patient_id(self, patient_id: str, days: int = 30) -> List[AsthmaCheckinLog]:
        start_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(AsthmaCheckinLog)
            .where(
                AsthmaCheckinLog.patient_id == patient_id,
                AsthmaCheckinLog.checkin_time >= start_date
            )
            .order_by(AsthmaCheckinLog.checkin_time.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_latest_checkin(self, patient_id: str) -> Optional[AsthmaCheckinLog]:
        stmt = (
            select(AsthmaCheckinLog)
            .where(AsthmaCheckinLog.patient_id == patient_id)
            .order_by(desc(AsthmaCheckinLog.checkin_time))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def count_checkins_in_days(self, patient_id: str, days: int = 7) -> int:
        start_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(func.count(AsthmaCheckinLog.id))
            .where(
                AsthmaCheckinLog.patient_id == patient_id,
                AsthmaCheckinLog.checkin_time >= start_date
            )
        )
        return self.db.scalar(stmt) or 0

    def get_recent_zone_counts(self, patient_id: str, days: int = 3) -> Dict[str, int]:
        start_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(AsthmaCheckinLog.action_zone, func.count(AsthmaCheckinLog.id))
            .where(
                AsthmaCheckinLog.patient_id == patient_id,
                AsthmaCheckinLog.checkin_time >= start_date
            )
            .group_by(AsthmaCheckinLog.action_zone)
        )
        return dict(self.db.execute(stmt).all())

class ReminderRepository:
    """Tầng Repository chuyên trách truy vấn Reminders."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_reminders(self, patient_id: str) -> List[AsthmaReminder]:
        stmt = (
            select(AsthmaReminder)
            .where(
                AsthmaReminder.patient_id == patient_id,
                AsthmaReminder.status.in_(["PENDING", "OVERDUE", "SNOOZED"])
            )
            .order_by(AsthmaReminder.scheduled_time.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, reminder_id: str) -> Optional[AsthmaReminder]:
        stmt = select(AsthmaReminder).where(AsthmaReminder.id == reminder_id)
        return self.db.scalars(stmt).first()

    def count_overdue_reminders(self, patient_id: str) -> int:
        stmt = (
            select(func.count(AsthmaReminder.id))
            .where(
                AsthmaReminder.patient_id == patient_id,
                AsthmaReminder.status == "OVERDUE"
            )
        )
        return self.db.scalar(stmt) or 0

    def update_status(self, reminder: AsthmaReminder, status: str, acknowledged: bool = False):
        reminder.status = status
        if acknowledged:
            reminder.acknowledged_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(reminder)
        return reminder
