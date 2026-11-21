"""Run the real API routers against a disposable PostgreSQL schema for browser E2E."""
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core import database
from backend.app.core.config import settings
from backend.app.api.v1.router import api_router
from backend.app.models import asthma, audit, identity  # noqa: F401 - register ORM models
from backend.app.models.identity import NurseAssignment, User
from backend.app.api.v1.endpoints import chat, escalations
from backend.app.orchestration.nodes.escalate import EscalationOutboxDispatcher
from backend.app.core.security import hash_password


_schema = f"w08_live_e2e_{uuid.uuid4().hex[:12]}"
with database.engine.begin() as connection:
    connection.execute(text(f'CREATE SCHEMA "{_schema}"'))
engine = create_engine(
    database.engine.url,
    connect_args={"options": f"-csearch_path={_schema} -ctimezone=UTC"},
    pool_pre_ping=True,
)
_schema_cleaned = False


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
database.SessionLocal = SessionLocal
escalations.SessionLocal = SessionLocal


def get_test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def seed_database():
    database.Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([
            User(id="w08-patient", username="w08.patient", full_name="Nguyễn Văn An",
                 password_hash=hash_password("Disposable-E2E-Password-01!"), role="patient",
                 patient_id="BN-2026-ASTHMA-01", is_demo=True),
            User(id="w08-nurse", username="w08.nurse", full_name="Điều dưỡng W08",
                 password_hash=hash_password("Disposable-E2E-Password-02!"), role="nurse",
                 is_demo=True),
        ])
        db.flush()
        db.add(NurseAssignment(nurse_id="w08-nurse", patient_id="BN-2026-ASTHMA-01"))
        db.add(asthma.AsthmaCarePlan(
            patient_id="BN-2026-ASTHMA-01", personal_best_pef=520,
            baseline_spo2=98, is_active=True,
        ))
        db.commit()


settings.DEMO_LOGIN_ENABLED = True
settings.COOKIE_SECURE = False
settings.CORS_ORIGINS = ["http://127.0.0.1:5174"]
chat.default_outbox_dispatcher = EscalationOutboxDispatcher(
    session_factory=SessionLocal,
    spool_path=Path(tempfile.gettempdir()) / f"aftercare-w08-{_schema}-outbox.jsonl",
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, on_startup=[seed_database])
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.dependency_overrides[database.get_db] = get_test_db
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def health():
    return {"status": "online", "database": "postgresql", "schema": _schema}


def drop_test_schema():
    global _schema_cleaned
    if _schema_cleaned:
        return
    engine.dispose()
    with database.engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{_schema}" CASCADE'))
    _schema_cleaned = True


@app.post("/__test/cleanup")
def cleanup_test_schema():
    drop_test_schema()
    return {"status": "cleaned"}


@app.on_event("shutdown")
def cleanup():
    drop_test_schema()
