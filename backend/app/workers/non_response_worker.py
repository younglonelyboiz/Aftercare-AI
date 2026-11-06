import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.app.core.database import SessionLocal
from backend.app.repositories.asthma_repositories import (
    CarePlanRepository,
    CheckinRepository,
    AlertTicketRepository
)
from backend.app.services.escalation_service import EscalationService

logger = logging.getLogger("NonResponseWorker")

class NonResponseWorker:
    """Background Worker định kỳ quét & phát hiện các ca mất liên lạc hoặc quá hạn Vùng Vàng 20 phút."""

    def __init__(self, interval_seconds: int = 30):
        self.interval_seconds = interval_seconds
        self.is_running = False

    async def scan_once(self) -> Dict[str, Any]:
        """Thực thi một chu kỳ quét (Dùng cho cả background loop và test suite)."""
        stats = {
            "yellow_followup_triggered": 0,
            "non_response_24h_triggered": 0,
            "non_response_12h_triggered": 0,
            "scanned_patients": 0
        }

        db = SessionLocal()
        try:
            care_plan_repo = CarePlanRepository(db)
            checkin_repo = CheckinRepository(db)
            ticket_repo = AlertTicketRepository(db)
            escalation_service = EscalationService(ticket_repo)

            active_plans = care_plan_repo.get_all_active_plans()
            stats["scanned_patients"] = len(active_plans)

            now = datetime.utcnow()

            for plan in active_plans:
                pid = plan.patient_id
                latest_chk = checkin_repo.get_latest_checkin(pid)

                # ==============================================================
                # 1. QUY TẮC VÙNG VÀNG 20 PHÚT (YELLOW-ZONE 20M FOLLOW-UP)
                # ==============================================================
                if latest_chk and latest_chk.action_zone == "YELLOW":
                    chk_time = latest_chk.checkin_time
                    if chk_time.tzinfo is not None:
                        chk_time = chk_time.replace(tzinfo=None)

                    delta_minutes = (now - chk_time).total_seconds() / 60.0

                    # Nếu đã quá 20 phút kể từ lúc check-in Vùng Vàng
                    if delta_minutes >= 20.0 and delta_minutes <= 180.0:
                        # Kiểm tra xem đã có vé OPEN cùng loại chưa
                        existing = ticket_repo.find_recent_open_ticket(
                            patient_id=pid,
                            alert_type="YELLOW_ZONE_FOLLOWUP_OVERDUE",
                            window_minutes=60
                        )
                        if not existing:
                            await escalation_service.create_or_escalate_ticket(
                                patient_id=pid,
                                priority="P1_HIGH",
                                alert_type="YELLOW_ZONE_FOLLOWUP_OVERDUE",
                                trigger_reason=(
                                    f"Bệnh nhân rơi vào Vùng Vàng cách đây {int(delta_minutes)} phút "
                                    f"(PEF {latest_chk.pef_value} L/m) nhưng chưa xác nhận an toàn hoặc chưa đo lại."
                                ),
                                checkin_id=latest_chk.id,
                                clinical_data={
                                    "pef_value": latest_chk.pef_value,
                                    "pef_percent": float(latest_chk.pef_percent) if latest_chk.pef_percent else None,
                                    "spo2": latest_chk.spo2_value,
                                    "checkin_time": latest_chk.checkin_time.isoformat()
                                }
                            )
                            stats["yellow_followup_triggered"] += 1

                # ==============================================================
                # 2. QUY TẮC MẤT LIÊN LẠC 12H VÀ 24H (NON-RESPONSE HANDLING)
                # ==============================================================
                last_active_time = latest_chk.checkin_time if latest_chk else plan.created_at
                if last_active_time.tzinfo is not None:
                    last_active_time = last_active_time.replace(tzinfo=None)

                hours_since_last = (now - last_active_time).total_seconds() / 3600.0

                # 2A. Quá 24h không có check-in -> P1_HIGH
                if hours_since_last >= 24.0:
                    existing_24h = ticket_repo.find_recent_open_ticket(
                        patient_id=pid,
                        alert_type="NON_RESPONSE_24H",
                        window_minutes=360 # 6 tiếng
                    )
                    if not existing_24h:
                        await escalation_service.create_or_escalate_ticket(
                            patient_id=pid,
                            priority="P1_HIGH",
                            alert_type="NON_RESPONSE_24H",
                            trigger_reason=(
                                f"Bệnh nhân không phản hồi hoặc bỏ lỡ check-in trong suốt {int(hours_since_last)} giờ qua. "
                                f"Mất liên lạc theo dõi ngoại trú."
                            ),
                            clinical_data={
                                "hours_overdue": round(hours_since_last, 1),
                                "last_active": last_active_time.isoformat()
                            }
                        )
                        stats["non_response_24h_triggered"] += 1

                # 2B. Quá 12h nhưng chưa tới 24h -> P2_MEDIUM
                elif hours_since_last >= 12.0:
                    existing_12h = ticket_repo.find_recent_open_ticket(
                        patient_id=pid,
                        alert_type="NON_RESPONSE_12H",
                        window_minutes=360
                    )
                    if not existing_12h:
                        await escalation_service.create_or_escalate_ticket(
                            patient_id=pid,
                            priority="P2_MEDIUM",
                            alert_type="NON_RESPONSE_12H",
                            trigger_reason=(
                                f"Bệnh nhân chưa thực hiện check-in định kỳ sau {int(hours_since_last)} giờ. "
                                f"Cần gửi lời nhắc nhở lần 1."
                            ),
                            clinical_data={
                                "hours_overdue": round(hours_since_last, 1),
                                "last_active": last_active_time.isoformat()
                            }
                        )
                        stats["non_response_12h_triggered"] += 1

        except Exception as e:
            logger.error(f"Lỗi trong chu kỳ quét NonResponseWorker: {str(e)}", exc_info=True)
        finally:
            db.close()

        return stats

    async def run_loop(self):
        """Vòng lặp chạy ngầm vĩnh viễn trong tiến trình FastAPI."""
        self.is_running = True
        logger.info(f"🚀 NonResponseWorker đã khởi động (chu kỳ quét: {self.interval_seconds}s)")
        while self.is_running:
            try:
                await self.scan_once()
            except Exception as e:
                logger.error(f"Lỗi worker loop: {str(e)}")
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        self.is_running = False
        logger.info("NonResponseWorker đã dừng.")

# Singleton instance
non_response_worker = NonResponseWorker(interval_seconds=30)

