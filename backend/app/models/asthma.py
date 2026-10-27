import uuid
from datetime import datetime, date, time
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Date, Time, 
    DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.core.database import Base

class AsthmaCarePlan(Base):
    """Bảng Kế hoạch chăm sóc Hen phế quản."""
    __tablename__ = "asthma_care_plans"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"plan-{uuid.uuid4()}")
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    personal_best_pef: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    baseline_spo2: Mapped[int] = mapped_column(Integer, default=98, nullable=False)
    action_plan_green: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_plan_yellow: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_plan_red: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doctor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ 1-N với các hạng mục thuốc & đo đạc
    items: Mapped[List["AsthmaCarePlanItem"]] = relationship(
        "AsthmaCarePlanItem", 
        back_populates="care_plan", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class AsthmaCarePlanItem(Base):
    """Bảng Các hạng mục thuốc duy trì, cắt cơn và giờ đo lường."""
    __tablename__ = "asthma_care_plan_items"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"item-{uuid.uuid4()}")
    care_plan_id: Mapped[str] = mapped_column(String(100), ForeignKey("asthma_care_plans.id", ondelete="CASCADE"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False) # CONTROLLER_MED, RELIEVER_MED, PEF_MEASURE, COMORBIDITY_MED
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schedule_times = Column(JSONB, default=list, nullable=False) # ['08:00', '20:00']
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    care_plan: Mapped["AsthmaCarePlan"] = relationship("AsthmaCarePlan", back_populates="items")

class AsthmaCheckinLog(Base):
    """Bảng Nhật ký Check-in chỉ số hô hấp và triệu chứng hen hàng ngày."""
    __tablename__ = "asthma_checkin_logs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"chk-{uuid.uuid4()}")
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    checkin_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    pef_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pef_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    spo2_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action_zone: Mapped[str] = mapped_column(String(20), nullable=False) # GREEN, YELLOW, RED
    symptoms = Column(JSONB, default=dict)
    meds_taken = Column(JSONB, default=dict)
    reliever_puffs: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class AsthmaReminder(Base):
    """Bảng Hàng đợi nhắc nhở uống thuốc & đo PEF."""
    __tablename__ = "asthma_reminders"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"rem-{uuid.uuid4()}")
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    item_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("asthma_care_plan_items.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False) # MEDICATION, PEF_CHECKIN, ALERT
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, ACKNOWLEDGED, SNOOZED, OVERDUE
    last_triggered_date: Mapped[date] = mapped_column(Date, default=date.today)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
