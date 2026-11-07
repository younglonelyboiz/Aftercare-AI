"""Idempotent migration; --demo seeds local demonstration accounts without replacing data."""
import argparse
import os
import secrets
from sqlalchemy import select
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models.identity import User, AuthSession, NurseAssignment, LoginThrottle, Conversation, ChatMessage, MemoryNote

TABLES = [User.__table__, AuthSession.__table__, NurseAssignment.__table__, LoginThrottle.__table__,
          Conversation.__table__, ChatMessage.__table__, MemoryNote.__table__]


def migrate(demo=False):
    Base.metadata.create_all(engine, tables=TABLES)
    with SessionLocal() as db:
        if demo:
            accounts = [("admin.demo", "Quản trị viên demo", "admin", None),
                        ("nurse.demo", "Điều dưỡng demo", "nurse", None)] + [
                (f"patient{n}.demo", name, "patient", f"BN-2026-ASTHMA-0{n}")
                for n, name in [(1, "Nguyễn Văn An"), (2, "Trần Thị Mai"), (3, "Lê Hoàng Long")]]
            for username, name, role, pid in accounts:
                user = db.scalar(select(User).where(User.username == username))
                if not user:
                    user = User(username=username, full_name=name, role=role, patient_id=pid,
                                password_hash=hash_password(secrets.token_urlsafe(32)), is_demo=True)
                    db.add(user)
                    db.flush()
                    if role == "nurse":
                        for n in range(1, 4):
                            db.add(NurseAssignment(nurse_id=user.id, patient_id=f"BN-2026-ASTHMA-0{n}"))
        elif os.getenv("BOOTSTRAP_ADMIN_PASSWORD"):
            if not db.scalar(select(User.id).where(User.role == "admin")):
                password = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]
                if len(password) < 10:
                    raise ValueError("BOOTSTRAP_ADMIN_PASSWORD cần ít nhất 10 ký tự")
                db.add(User(username="admin", full_name="Quản trị viên", role="admin", password_hash=hash_password(password)))
        db.commit()
    print("Identity/memory tables ready; existing data preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    migrate(parser.parse_args().demo)
