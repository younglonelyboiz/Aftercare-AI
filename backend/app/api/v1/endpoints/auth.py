from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (COOKIE_NAME, admin_user, check_origin, current_user,
    hash_password, start_session, token_hash, user_dto, verify_password)
from backend.app.models.identity import AuthSession, NurseAssignment, User, LoginThrottle

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(admin_user)])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class DemoLogin(BaseModel):
    user_id: str = Field(max_length=32)


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{3,100}$")
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=256)
    role: Literal["admin", "nurse", "patient"]
    patient_id: str | None = Field(default=None, max_length=100)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Literal["admin", "nurse", "patient"] | None = None
    patient_id: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=256)


class AssignmentsUpdate(BaseModel):
    patient_ids: list[str] = Field(max_length=200)


def validate_patient(patient_id: str | None):
    from backend.app.services.patient_context import load_profile
    if not patient_id:
        raise HTTPException(422, "Tài khoản bệnh nhân cần mã bệnh nhân.")
    try:
        load_profile(patient_id)
    except ValueError:
        raise HTTPException(422, "Mã bệnh nhân không tồn tại.")


@router.get("/demo-accounts")
def demo_accounts(db: Session = Depends(get_db)):
    if not settings.DEMO_LOGIN_ENABLED:
        return {"enabled": False, "accounts": []}
    users = db.scalars(select(User).where(User.is_demo.is_(True), User.is_active.is_(True)).order_by(User.role, User.username)).all()
    return {"enabled": True, "accounts": [{"id": u.id, "role": u.role,
            "full_name": u.full_name, "patient_id": u.patient_id} for u in users]}


@router.post("/login")
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    username = body.username.strip().lower()
    # Per-username persistent throttle; concurrent PostgreSQL updates serialize on this row.
    key = token_hash(username)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    now = datetime.utcnow()
    db.execute(insert(LoginThrottle).values(key=key, failures=0, reset_at=now + timedelta(minutes=15)).on_conflict_do_nothing())
    throttle = db.scalar(select(LoginThrottle).where(LoginThrottle.key == key).with_for_update())
    if throttle.reset_at <= now:
        throttle.failures = 0
        throttle.reset_at = now + timedelta(minutes=15)
    if throttle.failures >= 5:
        raise HTTPException(429, "Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút.")
    user = db.scalar(select(User).where(User.username == username))
    # Equal-cost password hashing even for an unknown username.
    valid = verify_password(body.password, user.password_hash) if user else bool(hash_password(body.password)) and False
    if not user or not valid or not user.is_active:
        throttle.failures += 1
        db.commit()
        raise HTTPException(401, "Tên đăng nhập hoặc mật khẩu không đúng.")
    throttle.failures = 0
    start_session(db, user, response, request.cookies.get(COOKIE_NAME))
    return user_dto(db, user)


@router.post("/demo-login")
def demo_login(body: DemoLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    if not settings.DEMO_LOGIN_ENABLED:
        raise HTTPException(404, "Đăng nhập demo đã tắt.")
    user = db.get(User, body.user_id)
    if not user or not user.is_demo or not user.is_active:
        raise HTTPException(403, "Tài khoản không được phép đăng nhập demo.")
    start_session(db, user, response, request.cookies.get(COOKIE_NAME))
    return user_dto(db, user)


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_dto(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(raw)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)


@admin_router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [user_dto(db, u) for u in db.scalars(select(User).order_by(User.created_at)).all()]


@admin_router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    username = body.username.lower()
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(409, "Tên đăng nhập đã tồn tại.")
    if body.role == "patient":
        validate_patient(body.patient_id)
    user = User(username=username, full_name=body.full_name.strip(), password_hash=hash_password(body.password),
                role=body.role, patient_id=body.patient_id if body.role == "patient" else None)
    db.add(user)
    db.commit()
    return user_dto(db, user)


@admin_router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_user)):
    # Serialize changes to active admins to prevent removing the last one concurrently.
    admins = db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True)).order_by(User.id).with_for_update()).all()
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    changes = body.model_dump(exclude_unset=True)
    if any(changes.get(k) is None for k in changes if k != "patient_id"):
        raise HTTPException(422, "Giá trị cập nhật không được để trống.")
    new_role = changes.get("role", user.role)
    active = changes.get("is_active", user.is_active)
    if user.id == actor.id and (new_role != "admin" or not active):
        raise HTTPException(409, "Không thể tự hạ quyền hoặc khóa tài khoản đang sử dụng.")
    if user in admins and len(admins) == 1 and (new_role != "admin" or not active):
        raise HTTPException(409, "Phải giữ ít nhất một admin đang hoạt động.")
    patient_id = changes.get("patient_id", user.patient_id)
    if new_role == "patient":
        validate_patient(patient_id)
    security_changed = any(k in changes for k in ("role", "patient_id", "is_active", "password"))
    for key in ("full_name", "role", "is_active"):
        if key in changes:
            setattr(user, key, changes[key])
    user.patient_id = patient_id if new_role == "patient" else None
    if body.password:
        user.password_hash = hash_password(body.password)
    if security_changed:
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    if new_role != "nurse":
        db.execute(delete(NurseAssignment).where(NurseAssignment.nurse_id == user.id))
    db.commit()
    return user_dto(db, user)


@admin_router.put("/users/{user_id}/assignments")
def update_assignments(user_id: str, body: AssignmentsUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.role != "nurse":
        raise HTTPException(422, "Chỉ phân công bệnh nhân cho tài khoản nurse.")
    for pid in set(body.patient_ids):
        validate_patient(pid)
    db.execute(delete(NurseAssignment).where(NurseAssignment.nurse_id == user.id))
    for pid in set(body.patient_ids):
        db.add(NurseAssignment(nurse_id=user.id, patient_id=pid))
    db.commit()
    return user_dto(db, user)
