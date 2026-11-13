import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.identity import AuthSession, NurseAssignment, User

COOKIE_NAME = "aftercare_session"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, digest = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request: Request):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        # Browser mutations must originate from the configured app, including login.
        if origin and origin not in settings.CORS_ORIGINS:
            raise HTTPException(403, "Nguồn yêu cầu không được phép.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Không chấp nhận yêu cầu từ trang bên ngoài.")


def session_user(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    session = db.get(AuthSession, token_hash(raw_token))
    if not session or session.expires_at <= datetime.utcnow():
        return None
    user = db.get(User, session.user_id)
    return user if user and user.is_active else None


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    check_origin(request)
    user = session_user(db, request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(401, "Vui lòng đăng nhập.")
    return user


def require_roles(*roles):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này.")
        return user
    return dependency


staff_user = require_roles("admin", "nurse")
admin_user = require_roles("admin")


def allowed_patient_ids(db: Session, user: User) -> set[str] | None:
    if user.role == "admin":
        return None
    if user.role == "patient":
        return {user.patient_id} if user.patient_id else set()
    return set(db.scalars(select(NurseAssignment.patient_id).where(NurseAssignment.nurse_id == user.id)).all())


def ensure_patient_access(db: Session, user: User, patient_id: str):
    allowed = allowed_patient_ids(db, user)
    if allowed is not None and patient_id not in allowed:
        raise HTTPException(403, "Bệnh nhân nằm ngoài phạm vi truy cập của bạn.")


def patient_scope(patient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_patient_access(db, user, patient_id)
    return user


def user_dto(db: Session, user: User):
    allowed = allowed_patient_ids(db, user)
    return {"id": user.id, "username": user.username, "full_name": user.full_name,
            "role": user.role, "patient_id": user.patient_id, "is_active": user.is_active,
            "is_demo": user.is_demo, "assigned_patient_ids": sorted(allowed) if allowed is not None else []}


def start_session(db: Session, user: User, response, previous: str | None = None):
    if previous:
        old = db.get(AuthSession, token_hash(previous))
        if old:
            db.delete(old)
    raw = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(raw), user_id=user.id,
                       expires_at=datetime.utcnow() + timedelta(hours=settings.SESSION_HOURS)))
    db.commit()
    response.set_cookie(COOKIE_NAME, raw, httponly=True, secure=settings.COOKIE_SECURE,
                        samesite="lax", max_age=settings.SESSION_HOURS * 3600, path="/")
    try:
        from backend.app.services.audit_service import current_actor_var

        current_actor_var.set(
            {
                "actor_id": str(user.username or user.id),
                "actor_role": str(user.role),
                "session_id": token_hash(raw)[:16],
                "patient_id": user.patient_id,
            }
        )
    except Exception:
        pass
