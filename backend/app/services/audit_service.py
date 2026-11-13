"""
Dịch vụ Nhật ký Kiểm toán Bất biến Toàn Hệ thống (`AuditService` & `AuditRequestMiddleware`) — [AUD-4].

Thực thi đầy đủ 6 bất biến kiểm toán (`AUD-INV-1` đến `AUD-INV-6`) theo tài liệu
`docs/ThietKe_CoChe_AuditLog_ToanHeThong.md`:
1. Mọi hành động (Xác thực, Hồ sơ lâm sàng, Check-in PEF, Điều phối Agent, Vé cảnh báo, Hội thoại, Tài liệu)
   đều được ghi vào bảng append-only `system_audit_logs`.
2. Tự động ẩn danh PII (`PIIRedactor`) và che mật khẩu/khóa bí mật trước khi lưu.
3. Ký chuỗi băm liên kết mật mã (`prev_hash` -> `record_hash`) để phát hiện mọi chỉnh sửa trái phép.
4. Không bao giờ làm gián đoạn luồng cấp cứu (Non-blocking fallback sang bộ nhớ và tệp spool).
"""
import contextvars
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.guardrails.pii_redactor import default_pii_redactor
from backend.app.models.audit import SystemAuditLog

logger = logging.getLogger("SystemAuditService")

GENESIS_PREV_HASH = "0" * 64
SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "raw_token",
    "token_hash",
    "cookie",
    "secret",
    "api_key",
    "authorization",
}
REDACTED_SECRET_TOKEN = "[ĐÃ_ẨN_BẢO_MẬT]"

DEFAULT_SYSTEM_AUDIT_SPOOL_PATH = (
    Path(__file__).resolve().parents[3]
    / "Evidence"
    / "W07"
    / "system_audit_spool.jsonl"
)

current_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_trace_id", default=None
)
current_actor_var: contextvars.ContextVar[Optional[Dict[str, Any]]] = (
    contextvars.ContextVar("current_actor", default=None)
)

_audit_session_factory: Optional[Callable[[], Session]] = None
_chain_lock = Lock()
_recent_system_events: List[Dict[str, Any]] = []
_last_memory_hash: str = GENESIS_PREV_HASH


def set_system_audit_session_factory(
    factory: Optional[Callable[[], Session]]
) -> None:
    """Cho phép kiểm thử tiêm `sessionmaker` tùy chỉnh cho `AuditService`."""
    global _audit_session_factory, _last_memory_hash
    _audit_session_factory = factory
    _last_memory_hash = GENESIS_PREV_HASH


def _get_db_session() -> Optional[Session]:
    if _audit_session_factory is not None:
        return _audit_session_factory()
    try:
        from backend.app.core.database import SessionLocal

        return SessionLocal()
    except Exception:
        return None


def get_current_trace_id() -> str:
    """Lấy mã `trace_id` của ngữ cảnh hiện tại hoặc sinh mới nếu chưa có."""
    tid = current_trace_id_var.get()
    if not tid:
        tid = f"trace-{uuid.uuid4().hex[:12]}"
        current_trace_id_var.set(tid)
    return tid


def get_current_actor() -> Dict[str, Any]:
    """Lấy thông tin tác nhân hiện tại từ `ContextVar`."""
    return current_actor_var.get() or {
        "actor_id": "system",
        "actor_role": "system",
        "session_id": None,
        "patient_id": None,
    }


def redact_audit_payload(
    data: Optional[Any],
    profile: Optional[Dict[str, Any]] = None,
) -> Any:
    """Ẩn danh đệ quy cả thông tin định danh cá nhân (PII) và các khóa bảo mật nhạy cảm."""
    if data is None:
        return {}
    if isinstance(data, str):
        return default_pii_redactor.redact_text(data, profile=profile)
    if isinstance(data, list):
        return [redact_audit_payload(item, profile=profile) for item in data]
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if key_lower in SENSITIVE_KEYS or any(
                s in key_lower for s in ("password", "secret", "token", "api_key")
            ):
                cleaned[str(k)] = REDACTED_SECRET_TOKEN
            elif key_lower in ("full_name", "name", "patient_name") and isinstance(v, str):
                cleaned[str(k)] = "Người bệnh"
            elif key_lower in ("phone", "phone_number", "mobile") and isinstance(v, str):
                cleaned[str(k)] = "[SỐ_ĐIỆN_THOẠI]"
            elif key_lower in ("email",) and isinstance(v, str):
                cleaned[str(k)] = "[ĐỊA_CHỈ_EMAIL]"
            elif key_lower in ("cccd", "cmnd", "national_id") and isinstance(v, str):
                cleaned[str(k)] = "[MÃ_ĐỊNH_DANH]"
            elif key_lower in ("address", "street_address") and isinstance(v, str):
                cleaned[str(k)] = "[ĐỊA_CHỈ]"
            else:
                cleaned[str(k)] = redact_audit_payload(v, profile=profile)
        return cleaned
    return data


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, sort_keys=True, default=str)


def compute_record_hash(
    *,
    prev_hash: str,
    trace_id: str,
    actor_id: str,
    action_code: str,
    resource_id: Optional[str],
    after_state: Any,
    created_at_iso: str,
) -> str:
    """Tính mã băm liên kết mật mã SHA-256 (`AUD-INV-4`)."""
    raw = (
        f"{prev_hash}|{trace_id}|{actor_id}|{action_code}|"
        f"{resource_id or ''}|{_canonical_json(after_state)}|{created_at_iso}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_http_action(
    method: str, path: str, status_code: int
) -> Tuple[str, str, Optional[str], Optional[str], str]:
    """Ánh xạ `(method, path, status_code)` sang `(category, action_code, resource_type, resource_id, severity)`."""
    m = method.upper()
    clean_path = path.split("?")[0]

    if status_code in (401, 403):
        if clean_path.endswith("/auth/login"):
            return ("AUTH", "AUTH.LOGIN_FAILED", "AuthSession", None, "WARNING")
        return ("AUTH", "AUTH.ACCESS_DENIED", "Endpoint", clean_path, "HIGH")

    # 1. AUTH & ADMIN
    if clean_path.endswith("/auth/login") and m == "POST":
        return ("AUTH", "AUTH.LOGIN_SUCCESS", "AuthSession", None, "INFO")
    if clean_path.endswith("/auth/demo-login") and m == "POST":
        return ("AUTH", "AUTH.DEMO_LOGIN", "AuthSession", None, "INFO")
    if clean_path.endswith("/auth/logout") and m == "POST":
        return ("AUTH", "AUTH.LOGOUT", "AuthSession", None, "INFO")
    if "/admin/users" in clean_path:
        parts = clean_path.strip("/").split("/")
        uid = parts[-1] if len(parts) >= 4 and parts[-1] != "users" else None
        if clean_path.endswith("/assignments") and m == "PUT":
            uid = parts[-2]
            return ("ADMIN", "ADMIN.NURSE_ASSIGNMENT_UPDATED", "NurseAssignment", uid, "HIGH")
        if m == "POST":
            return ("ADMIN", "ADMIN.USER_CREATED", "User", uid, "HIGH")
        if m in ("PATCH", "PUT"):
            return ("ADMIN", "ADMIN.USER_UPDATED", "User", uid, "HIGH")

    # 2. CLINICAL & CARE TRACKER
    if "/care-tracker/checkin" in clean_path and m == "POST":
        return ("CLINICAL", "CLINICAL.PEF_CHECKIN_SUBMIT", "DailyCheckin", None, "INFO")
    if "/care-tracker/care-plans" in clean_path:
        parts = clean_path.strip("/").split("/")
        pid = parts[-1] if parts[-1] != "care-plans" else None
        if m == "POST":
            return ("CLINICAL", "CLINICAL.CARE_PLAN_UPDATED", "CarePlan", pid, "HIGH")
        return ("CLINICAL", "CLINICAL.CARE_PLAN_VIEWED", "CarePlan", pid, "INFO")
    if "/care-tracker/reminders/" in clean_path and m == "POST":
        parts = clean_path.strip("/").split("/")
        rid = parts[-2] if len(parts) >= 2 else None
        return ("CLINICAL", "CLINICAL.MEDICATION_ADHERENCE_LOG", "Reminder", rid, "INFO")
    if "/care-tracker/reset-demo" in clean_path and m == "POST":
        return ("ADMIN", "ADMIN.DEMO_DATA_RESET", "System", None, "WARNING")
    if "/screener/" in clean_path and m == "POST":
        return ("CLINICAL", "CLINICAL.SCREENER_EVALUATE", "SymptomScreener", None, "HIGH")
    if "/patients/" in clean_path and m == "GET":
        pid = clean_path.strip("/").split("/")[-1]
        return ("CLINICAL", "CLINICAL.PROFILE_VIEW", "PatientProfile", pid, "INFO")

    # 3. ESCALATION & ALERTS
    if "/escalations/tickets/" in clean_path and m == "POST":
        parts = clean_path.strip("/").split("/")
        tid = parts[-2] if len(parts) >= 2 else None
        if clean_path.endswith("/acknowledge"):
            return ("ESCALATION", "ESCALATION.TICKET_ACKNOWLEDGED", "AlertTicket", tid, "HIGH")
        if clean_path.endswith("/resolve"):
            return ("ESCALATION", "ESCALATION.TICKET_RESOLVED", "AlertTicket", tid, "HIGH")
    if clean_path.endswith("/safety-confirm-20m") and m == "POST":
        parts = clean_path.strip("/").split("/")
        pid = parts[-2] if len(parts) >= 2 else None
        return ("ESCALATION", "ESCALATION.PATIENT_SAFETY_CONFIRMED_20M", "AlertTicket", pid, "HIGH")
    if clean_path.endswith("/scan-non-response") and m == "POST":
        return ("WORKER", "WORKER.NON_RESPONSE_SWEEP", "NonResponseWorker", None, "INFO")

    # 4. CHAT & CONVERSATIONS
    if clean_path.endswith("/chat/chat") and m == "POST":
        return ("AGENT", "CHAT.MESSAGE_SUBMITTED", "ChatTurn", None, "INFO")
    if "/chat/conversations" in clean_path:
        parts = clean_path.strip("/").split("/")
        cid = parts[-1] if parts[-1] != "conversations" else None
        if m == "POST":
            return ("CHAT", "CHAT.CONVERSATION_CREATED", "Conversation", cid, "INFO")
        if m == "PATCH":
            return ("CHAT", "CHAT.CONVERSATION_RENAMED", "Conversation", cid, "INFO")
        if m == "DELETE":
            return ("CHAT", "CHAT.CONVERSATION_DELETED", "Conversation", cid, "WARNING")

    # 5. DOCUMENTS
    if "/documents/view/" in clean_path and m == "GET":
        doc_tag = clean_path.strip("/").split("/")[-1]
        return ("DOCUMENT", "DOCUMENT.PDF_VIEWED", "ClinicalDocument", doc_tag, "INFO")

    return ("SYSTEM", f"HTTP.{m}", "Endpoint", clean_path, "INFO")


class AuditService:
    """Dịch vụ trung tâm ghi nhận và kiểm định nhật ký kiểm toán bất biến toàn hệ thống."""

    def __init__(self, spool_path: Optional[Path] = None):
        self.spool_path = spool_path or DEFAULT_SYSTEM_AUDIT_SPOOL_PATH

    def record_event(
        self,
        *,
        category: str,
        action_code: str,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        http_method: str = "INTERNAL",
        http_path: Optional[str] = None,
        status_code: int = 200,
        severity: str = "INFO",
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client_ip_hash: Optional[str] = None,
        profile: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Ghi 1 bản ghi kiểm toán bất biến vào `system_audit_logs` kèm chuỗi băm SHA-256."""
        global _last_memory_hash

        ctx_actor = get_current_actor()
        resolved_trace_id = trace_id or get_current_trace_id()
        resolved_actor_id = actor_id or ctx_actor.get("actor_id") or "system"
        resolved_actor_role = actor_role or ctx_actor.get("actor_role") or "system"
        resolved_session_id = session_id or ctx_actor.get("session_id")
        resolved_patient_id = patient_id or ctx_actor.get("patient_id")

        clean_before = redact_audit_payload(before_state or {}, profile=profile)
        clean_after = redact_audit_payload(after_state or {}, profile=profile)
        clean_meta = redact_audit_payload(metadata or {}, profile=profile)

        now_dt = datetime.now(timezone.utc).replace(tzinfo=None).replace(microsecond=0)
        now_iso = now_dt.isoformat()
        event_id = uuid.uuid4().hex

        with _chain_lock:
            own_session = False
            session = db
            if session is None:
                session = _get_db_session()
                own_session = session is not None

            prev_hash = _last_memory_hash
            next_seq = len(_recent_system_events) + 1
            if session is not None:
                try:
                    last_row = session.scalar(
                        select(SystemAuditLog).order_by(
                            desc(SystemAuditLog.chain_seq), desc(SystemAuditLog.id)
                        )
                    )
                    if last_row is not None and last_row.record_hash:
                        prev_hash = last_row.record_hash
                        next_seq = int(last_row.chain_seq or 0) + 1
                    else:
                        prev_hash = GENESIS_PREV_HASH
                        next_seq = 1
                except Exception:
                    pass

            record_hash = compute_record_hash(
                prev_hash=prev_hash,
                trace_id=resolved_trace_id,
                actor_id=resolved_actor_id,
                action_code=action_code,
                resource_id=resource_id,
                after_state=clean_after,
                created_at_iso=now_iso,
            )

            record_dict = {
                "id": event_id,
                "chain_seq": next_seq,
                "trace_id": resolved_trace_id,
                "session_id": resolved_session_id,
                "actor_id": resolved_actor_id,
                "actor_role": resolved_actor_role,
                "patient_id": resolved_patient_id,
                "category": category,
                "action_code": action_code,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "http_method": http_method,
                "http_path": http_path,
                "status_code": status_code,
                "severity": severity,
                "before_state": clean_before,
                "after_state": clean_after,
                "metadata_json": clean_meta,
                "client_ip_hash": client_ip_hash,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "created_at": now_iso,
            }

            persisted = False
            if session is not None:
                try:
                    row = SystemAuditLog(
                        id=event_id,
                        chain_seq=next_seq,
                        trace_id=resolved_trace_id,
                        session_id=resolved_session_id,
                        actor_id=resolved_actor_id,
                        actor_role=resolved_actor_role,
                        patient_id=resolved_patient_id,
                        category=category,
                        action_code=action_code,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        http_method=http_method,
                        http_path=http_path,
                        status_code=status_code,
                        severity=severity,
                        before_state=clean_before,
                        after_state=clean_after,
                        metadata_json=clean_meta,
                        client_ip_hash=client_ip_hash,
                        prev_hash=prev_hash,
                        record_hash=record_hash,
                        created_at=now_dt,
                    )
                    session.add(row)
                    session.commit()
                    persisted = True
                    _last_memory_hash = record_hash
                except Exception as exc:
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    logger.debug("Dự phòng ghi tệp spool cho system_audit_logs (%s)", exc)
                finally:
                    if own_session:
                        try:
                            session.close()
                        except Exception:
                            pass

            if not persisted:
                _last_memory_hash = record_hash
                try:
                    self.spool_path.parent.mkdir(parents=True, exist_ok=True)
                    with self.spool_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(record_dict, ensure_ascii=False) + "\n")
                except Exception:
                    pass

            if len(_recent_system_events) >= 500:
                _recent_system_events.pop(0)
            _recent_system_events.append(record_dict)

            return record_dict

    def verify_chain(
        self, db: Optional[Session] = None, limit: int = 1000
    ) -> Dict[str, Any]:
        """Kiểm định tính toàn vẹn mật mã của chuỗi băm trong `system_audit_logs` (`AUD-INV-4`)."""
        own_session = False
        session = db
        if session is None:
            session = _get_db_session()
            own_session = session is not None

        if session is None:
            return {
                "valid": True,
                "checked_records": 0,
                "broken_at_id": None,
                "broken_trace_id": None,
                "reason": "Không có kết nối cơ sở dữ liệu kiểm toán.",
            }

        try:
            rows: List[SystemAuditLog] = list(
                session.scalars(
                    select(SystemAuditLog)
                    .order_by(SystemAuditLog.chain_seq.asc())
                    .limit(limit)
                ).all()
            )
            expected_prev = GENESIS_PREV_HASH
            for idx, row in enumerate(rows):
                if idx > 0 and row.prev_hash != expected_prev:
                    return {
                        "valid": False,
                        "checked_records": idx + 1,
                        "broken_at_id": row.id,
                        "broken_trace_id": row.trace_id,
                        "reason": f"Đứt gãy liên kết prev_hash tại bản ghi {row.id}.",
                    }
                created_iso = (
                    row.created_at.replace(microsecond=0).isoformat()
                    if row.created_at
                    else ""
                )
                recomputed = compute_record_hash(
                    prev_hash=row.prev_hash,
                    trace_id=row.trace_id,
                    actor_id=row.actor_id,
                    action_code=row.action_code,
                    resource_id=row.resource_id,
                    after_state=row.after_state or {},
                    created_at_iso=created_iso,
                )
                if recomputed != row.record_hash:
                    return {
                        "valid": False,
                        "checked_records": idx + 1,
                        "broken_at_id": row.id,
                        "broken_trace_id": row.trace_id,
                        "reason": f"Sai lệch mã băm record_hash tại bản ghi {row.id} (dữ liệu đã bị sửa đổi trái phép).",
                    }
                expected_prev = row.record_hash

            return {
                "valid": True,
                "checked_records": len(rows),
                "broken_at_id": None,
                "broken_trace_id": None,
                "tail_hash": expected_prev if rows else GENESIS_PREV_HASH,
            }
        finally:
            if own_session:
                session.close()


default_audit_service = AuditService()


def _resolve_request_actor(request: Request) -> Dict[str, Any]:
    """Trích xuất danh tính người dùng từ cookie phiên đăng nhập nếu có."""
    try:
        from backend.app.core.security import COOKIE_NAME, session_user, token_hash

        raw_token = request.cookies.get(COOKIE_NAME)
        if not raw_token:
            return {
                "actor_id": "anonymous",
                "actor_role": "anonymous",
                "session_id": None,
                "patient_id": None,
            }
        session = _get_db_session()
        if session is None:
            return {
                "actor_id": "anonymous",
                "actor_role": "anonymous",
                "session_id": token_hash(raw_token)[:16],
                "patient_id": None,
            }
        try:
            user = session_user(session, raw_token)
            if user is not None:
                return {
                    "actor_id": str(user.username or user.id),
                    "actor_role": str(user.role),
                    "session_id": token_hash(raw_token)[:16],
                    "patient_id": user.patient_id,
                }
        finally:
            session.close()
    except Exception:
        pass
    return {
        "actor_id": "anonymous",
        "actor_role": "anonymous",
        "session_id": None,
        "patient_id": None,
    }


def _should_audit_http_request(method: str, path: str, status_code: int) -> bool:
    """Quyết định các yêu cầu HTTP cần tự động ghi vào `system_audit_logs`."""
    if not path.startswith("/api/"):
        return False
    # Không tự ghi đè khi quản trị viên chỉ đang đọc bảng audit hoặc đọc danh sách tài khoản demo
    if path.startswith("/api/v1/audit") and method.upper() == "GET" and status_code < 400:
        return False
    if path.endswith("/auth/demo-accounts") or path.endswith("/auth/me"):
        return status_code in (401, 403)
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    if status_code in (401, 403):
        return True
    # Ghi nhận các truy vấn đọc hồ sơ lâm sàng và mở tài liệu PDF
    if any(
        seg in path
        for seg in ("/patients/", "/documents/view/", "/care-tracker/care-plans/")
    ):
        return True
    return False


class AuditRequestMiddleware(BaseHTTPMiddleware):
    """Middleware tự động gắn mã `trace_id`, trích xuất tác nhân và ghi nhận mọi hành động HTTP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_trace = request.headers.get("X-Trace-Id") or request.headers.get(
            "x-trace-id"
        )
        trace_id = (
            incoming_trace.strip()
            if incoming_trace and re.match(r"^[a-zA-Z0-9_.-]{6,64}$", incoming_trace.strip())
            else f"trace-{uuid.uuid4().hex[:12]}"
        )
        actor_info = _resolve_request_actor(request)

        t_token = current_trace_id_var.set(trace_id)
        a_token = current_actor_var.set(actor_info)
        try:
            response: Response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id

            if _should_audit_http_request(
                request.method, request.url.path, response.status_code
            ):
                # Nếu vừa đăng nhập thành công thì đọc lại cookie mới trong response
                if request.url.path.endswith(("/auth/login", "/auth/demo-login")) and response.status_code < 400:
                    actor_info = get_current_actor()

                category, action_code, res_type, res_id, severity = classify_http_action(
                    request.method, request.url.path, response.status_code
                )
                client_host = request.client.host if request.client else "unknown"
                ip_hash = hashlib.sha256(client_host.encode("utf-8")).hexdigest()[:32]

                default_audit_service.record_event(
                    category=category,
                    action_code=action_code,
                    actor_id=actor_info.get("actor_id"),
                    actor_role=actor_info.get("actor_role"),
                    patient_id=actor_info.get("patient_id") or (res_id if res_type in ("PatientProfile", "CarePlan") else None),
                    session_id=actor_info.get("session_id"),
                    trace_id=trace_id,
                    resource_type=res_type,
                    resource_id=res_id,
                    http_method=request.method.upper(),
                    http_path=request.url.path,
                    status_code=response.status_code,
                    severity=severity,
                    after_state={"status_code": response.status_code},
                    client_ip_hash=ip_hash,
                )
            return response
        finally:
            current_trace_id_var.reset(t_token)
            current_actor_var.reset(a_token)


__all__ = [
    "AuditRequestMiddleware",
    "AuditService",
    "GENESIS_PREV_HASH",
    "classify_http_action",
    "compute_record_hash",
    "current_actor_var",
    "current_trace_id_var",
    "default_audit_service",
    "get_current_actor",
    "get_current_trace_id",
    "redact_audit_payload",
    "set_system_audit_session_factory",
]
