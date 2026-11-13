"""
Bộ điều phối leo thang cảnh báo kèm Hàng đợi Dự phòng Bền vững (Escalation Outbox Pattern) — [W07-T5.2].

Đảm bảo nguyên tắc "Non-blocking AI" và "Zero-Lost Ticket":
- Nếu `EscalationService.create_or_escalate_ticket` thành công ngay lập tức: ghi nhận `SENT` và trả về `ticket.id`.
- Nếu cơ sở dữ liệu hoặc dịch vụ cảnh báo gặp sự cố tạm thời (ví dụ: mất kết nối DB trong 30 giây):
  1. Phản hồi khẩn cấp cho bệnh nhân KHÔNG bị chặn.
  2. Yêu cầu tạo vé được lưu vào bảng `escalation_outbox` (hoặc tệp hàng đợi dự phòng JSONL trên đĩa
     nếu kết nối DB bị ngắt hoàn toàn).
  3. Khi DB hoạt động trở lại, phương thức `flush_pending()` sẽ tự động đồng bộ tệp dự phòng vào
     bảng `escalation_outbox`, thực thi lại việc tạo `AlertTicket` và đánh dấu `status = "SENT"`.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.audit import EscalationOutbox

logger = logging.getLogger("EscalationOutbox")

DEFAULT_SPOOL_PATH = (
    Path(__file__).resolve().parents[4]
    / "Evidence"
    / "W07"
    / "escalation_outbox_spool.jsonl"
)


class EscalationOutboxDispatcher:
    """Bộ điều phối tạo vé cảnh báo có cơ chế hàng đợi dự phòng và tự động thử lại (Retry Outbox)."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], Session]] = None,
        spool_path: Optional[Path] = None,
    ):
        self._session_factory = session_factory
        self.spool_path = spool_path or DEFAULT_SPOOL_PATH
        self._memory_spool: List[Dict[str, Any]] = []

    def _get_session(self) -> Optional[Session]:
        if self._session_factory is not None:
            return self._session_factory()
        try:
            from backend.app.core.database import SessionLocal

            return SessionLocal()
        except Exception:
            return None

    def _write_disk_spool(self, payload: Dict[str, Any]) -> None:
        self._memory_spool.append(payload)
        try:
            self.spool_path.parent.mkdir(parents=True, exist_ok=True)
            with self.spool_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception:
            logger.exception("Không ghi được tệp spool dự phòng tại %s", self.spool_path)

    def _enqueue_outbox_record(
        self,
        payload: Dict[str, Any],
        error_msg: str,
        db: Optional[Session] = None,
    ) -> str:
        outbox_id = payload.get("id") or uuid.uuid4().hex
        payload["id"] = outbox_id
        payload["last_error"] = error_msg

        own_session = False
        session = db
        if session is None:
            session = self._get_session()
            own_session = session is not None

        if session is not None:
            try:
                existing = session.get(EscalationOutbox, outbox_id)
                if existing is None:
                    row = EscalationOutbox(
                        id=outbox_id,
                        trace_id=payload.get("trace_id"),
                        patient_id=payload["patient_id"],
                        patient_name=payload.get("patient_name"),
                        priority=payload["priority"],
                        alert_type=payload["alert_type"],
                        trigger_reason=payload["trigger_reason"],
                        clinical_data=payload.get("clinical_data") or {},
                        status="PENDING",
                        attempts=1,
                        last_error=error_msg[:1000],
                    )
                    session.add(row)
                else:
                    existing.attempts = (existing.attempts or 0) + 1
                    existing.last_error = error_msg[:1000]
                    existing.updated_at = datetime.utcnow()
                session.commit()
                if own_session:
                    session.close()
                return outbox_id
            except Exception as db_exc:
                try:
                    session.rollback()
                except Exception:
                    pass
                if own_session:
                    try:
                        session.close()
                    except Exception:
                        pass
                logger.warning(
                    "Bảng escalation_outbox tạm thời không ghi được (%s); chuyển sang spool dự phòng.",
                    db_exc,
                )

        # Dự phòng cấp 2 khi DB hoàn toàn ngắt kết nối
        self._write_disk_spool(payload)
        return outbox_id

    async def dispatch(
        self,
        escalation_service: Any,
        *,
        patient_id: str,
        priority: str,
        alert_type: str,
        trigger_reason: str,
        patient_name: Optional[str] = None,
        clinical_data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[str]:
        """Thử tạo vé cảnh báo ngay; nếu lỗi thì lưu vào `escalation_outbox` / spool để thử lại."""
        payload = {
            "id": uuid.uuid4().hex,
            "trace_id": trace_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "priority": priority,
            "alert_type": alert_type,
            "trigger_reason": trigger_reason,
            "clinical_data": clinical_data or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        try:
            ticket = await escalation_service.create_or_escalate_ticket(
                patient_id=patient_id,
                priority=priority,
                alert_type=alert_type,
                trigger_reason=trigger_reason,
                patient_name=patient_name,
                clinical_data=clinical_data or {},
            )
            return ticket.id
        except Exception as exc:
            logger.critical(
                "Tạo vé cảnh báo thất bại tức thời cho bệnh nhân %s (%s); đưa vào EscalationOutbox.",
                patient_id,
                exc,
            )
            self._enqueue_outbox_record(payload, error_msg=str(exc), db=db)
            return None

    async def flush_pending(
        self,
        escalation_service: Any,
        db: Optional[Session] = None,
    ) -> List[str]:
        """Đồng bộ các bản ghi từ spool/bảng `escalation_outbox` đang `PENDING` và tạo lại vé cảnh báo."""
        own_session = False
        session = db
        if session is None:
            session = self._get_session()
            own_session = session is not None

        if session is None:
            return []

        recovered_ticket_ids: List[str] = []
        try:
            # 1. Nạp các mục từ bộ nhớ / tệp spool đĩa vào bảng escalation_outbox nếu chưa có
            spool_items = list(self._memory_spool)
            if self.spool_path.exists():
                try:
                    for line in self.spool_path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            parsed = json.loads(line)
                            if not any(x.get("id") == parsed.get("id") for x in spool_items):
                                spool_items.append(parsed)
                except Exception:
                    pass

            for item in spool_items:
                oid = item.get("id") or uuid.uuid4().hex
                if session.get(EscalationOutbox, oid) is None:
                    session.add(
                        EscalationOutbox(
                            id=oid,
                            trace_id=item.get("trace_id"),
                            patient_id=item["patient_id"],
                            patient_name=item.get("patient_name"),
                            priority=item["priority"],
                            alert_type=item["alert_type"],
                            trigger_reason=item["trigger_reason"],
                            clinical_data=item.get("clinical_data") or {},
                            status="PENDING",
                            attempts=1,
                            last_error=item.get("last_error"),
                        )
                    )
            session.commit()

            # 2. Quét toàn bộ bản ghi PENDING trong bảng escalation_outbox để gửi lại
            pending_rows = session.scalars(
                select(EscalationOutbox)
                .where(EscalationOutbox.status == "PENDING")
                .order_by(EscalationOutbox.created_at)
            ).all()

            all_succeeded = True
            for row in pending_rows:
                try:
                    ticket = await escalation_service.create_or_escalate_ticket(
                        patient_id=row.patient_id,
                        priority=row.priority,
                        alert_type=row.alert_type,
                        trigger_reason=row.trigger_reason,
                        patient_name=row.patient_name,
                        clinical_data=row.clinical_data or {},
                    )
                    row.status = "SENT"
                    row.ticket_id = ticket.id
                    row.attempts = (row.attempts or 0) + 1
                    row.updated_at = datetime.utcnow()
                    recovered_ticket_ids.append(ticket.id)
                except Exception as retry_exc:
                    all_succeeded = False
                    row.attempts = (row.attempts or 0) + 1
                    row.last_error = str(retry_exc)[:1000]
                    row.updated_at = datetime.utcnow()

            session.commit()

            if all_succeeded:
                self._memory_spool.clear()
                if self.spool_path.exists():
                    try:
                        self.spool_path.unlink()
                    except Exception:
                        pass

            return recovered_ticket_ids
        finally:
            if own_session:
                session.close()


default_outbox_dispatcher = EscalationOutboxDispatcher()

__all__ = [
    "DEFAULT_SPOOL_PATH",
    "EscalationOutboxDispatcher",
    "default_outbox_dispatcher",
]

