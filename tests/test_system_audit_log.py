"""
KIỂM THỬ CƠ CHẾ NHẬT KÝ KIỂM TOÁN BẤT BIẾN TOÀN HỆ THỐNG (SYSTEM-WIDE IMMUTABLE AUDIT LOG) — [AUD-1 ĐẾN AUD-5].

Kiểm định toàn diện 6 bất biến kiểm toán (`AUD-INV-1` đến `AUD-INV-6`) theo tài liệu
`docs/ThietKe_CoChe_AuditLog_ToanHeThong.md`:
1. `AUD-INV-1` (Strict Append-Only): Bảng `system_audit_logs` chặn cứng mọi thao tác UPDATE / DELETE bằng `ImmutableAuditRecordError`.
2. `AUD-INV-2` (Complete Action Coverage): Ghi nhận đầy đủ các nhóm hành động `AUTH`, `CLINICAL`, `AGENT`, `ESCALATION`, `CHAT`, `DOCUMENT` qua cả `AuditService` và `AuditRequestMiddleware`.
3. `AUD-INV-3` (Zero Raw PII & Secret Redaction): Tự động che mật khẩu, token, họ tên, số điện thoại, căn cước công dân, email trong `before_state`, `after_state`, `metadata_json`.
4. `AUD-INV-4` (Tamper-Evident Hash Chain): Chuỗi băm `prev_hash -> record_hash` hợp lệ khi dữ liệu nguyên vẹn (`valid=True`) và phát hiện ngay lập tức khi có can thiệp sửa dữ liệu bằng SQL thô (`valid=False`).
5. `AUD-INV-5` & `AUD-INV-6` (Unified Traceability & Read-Only Admin API): Truy vết hợp nhất cùng `trace_id` qua `/api/v1/audit/traces/{trace_id}`, `/api/v1/audit/events` và `/api/v1/audit/verify-chain`.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.v1.endpoints import audit as audit_endpoint
from backend.app.core.database import get_db
from backend.app.core.security import admin_user
from backend.app.db.migrate_audit_tables import migrate_audit_tables
from backend.app.models.audit import (
    ImmutableAuditRecordError,
    SystemAuditLog,
)
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.nodes.finalize_audit import set_audit_session_factory
from backend.app.orchestration.state import make_initial_state
from backend.app.services.audit_service import (
    AuditRequestMiddleware,
    GENESIS_PREV_HASH,
    default_audit_service,
    set_system_audit_session_factory,
)


@pytest.fixture
def system_audit_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    migrate_audit_tables(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    set_audit_session_factory(factory)
    set_system_audit_session_factory(factory)
    yield engine, factory
    set_audit_session_factory(None)
    set_system_audit_session_factory(None)


def test_aud_inv1_system_audit_log_is_strictly_append_only(system_audit_db):
    """AUD-INV-1: Cố tình UPDATE hoặc DELETE trên SystemAuditLog phải ném ImmutableAuditRecordError."""
    _, factory = system_audit_db

    rec = default_audit_service.record_event(
        category="AUTH",
        action_code="AUTH.LOGIN_SUCCESS",
        actor_id="nurse.demo",
        actor_role="nurse",
        trace_id="trace-immut-01",
        after_state={"status": "logged_in"},
    )
    assert rec["id"]

    with factory() as db:
        row = db.get(SystemAuditLog, rec["id"])
        assert row is not None
        row.action_code = "AUTH.TAMPERED"
        with pytest.raises(ImmutableAuditRecordError):
            db.commit()
        db.rollback()

        row_del = db.get(SystemAuditLog, rec["id"])
        db.delete(row_del)
        with pytest.raises(ImmutableAuditRecordError):
            db.commit()
        db.rollback()


def test_aud_inv3_pii_and_secret_redaction_in_audit_payloads(system_audit_db):
    """AUD-INV-3: Mật khẩu, token, họ tên, số điện thoại, CCCD và email bị che hoàn toàn trong SystemAuditLog."""
    _, factory = system_audit_db

    rec = default_audit_service.record_event(
        category="CLINICAL",
        action_code="CLINICAL.PEF_CHECKIN_SUBMIT",
        actor_id="patient1.demo",
        actor_role="patient",
        patient_id="BN-2026-ASTHMA-01",
        trace_id="trace-pii-01",
        before_state={
            "password": "SuperSecretPassword123!",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "full_name": "Nguyễn Văn An",
            "phone": "0912345678",
        },
        after_state={
            "note": "Bệnh nhân Nguyễn Văn An gọi từ số 0912345678, CCCD 001098123456, email an@example.com",
            "pef_value": 290,
        },
        profile={
            "patient_info": {
                "full_name": "Nguyễn Văn An",
                "patient_id": "BN-2026-ASTHMA-01",
            }
        },
    )

    with factory() as db:
        row = db.get(SystemAuditLog, rec["id"])
        assert row is not None
        serialized = f"{row.before_state} {row.after_state}"
        assert "SuperSecretPassword123!" not in serialized
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in serialized
        assert "Nguyễn Văn An" not in serialized
        assert "0912345678" not in serialized
        assert "001098123456" not in serialized
        assert "an@example.com" not in serialized
        assert row.after_state["pef_value"] == 290


def test_aud_inv4_cryptographic_hash_chain_and_tamper_detection(system_audit_db):
    """AUD-INV-4: Kiểm định chuỗi băm liên kết mật mã và phát hiện hành vi sửa trực tiếp qua SQL thô."""
    engine, factory = system_audit_db

    r1 = default_audit_service.record_event(
        category="AUTH",
        action_code="AUTH.LOGIN_SUCCESS",
        actor_id="nurse.demo",
        actor_role="nurse",
        trace_id="trace-chain-1",
        after_state={"step": 1},
    )
    r2 = default_audit_service.record_event(
        category="ESCALATION",
        action_code="ESCALATION.TICKET_ACKNOWLEDGED",
        actor_id="nurse.demo",
        actor_role="nurse",
        patient_id="BN-2026-ASTHMA-02",
        resource_id="ticket-001",
        trace_id="trace-chain-2",
        after_state={"status": "ACKNOWLEDGED"},
    )
    r3 = default_audit_service.record_event(
        category="ESCALATION",
        action_code="ESCALATION.TICKET_RESOLVED",
        actor_id="nurse.demo",
        actor_role="nurse",
        patient_id="BN-2026-ASTHMA-02",
        resource_id="ticket-001",
        trace_id="trace-chain-3",
        after_state={"status": "RESOLVED"},
    )

    assert r1["prev_hash"] == GENESIS_PREV_HASH
    assert r2["prev_hash"] == r1["record_hash"]
    assert r3["prev_hash"] == r2["record_hash"]

    with factory() as db:
        verdict_ok = default_audit_service.verify_chain(db=db)
        assert verdict_ok["valid"] is True
        assert verdict_ok["checked_records"] == 3

    # Mô phỏng kẻ tấn công can thiệp trực tiếp ở tầng SQL (bỏ qua ORM hook) để sửa bản ghi thứ 2
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE system_audit_logs SET action_code = 'ESCALATION.FORGED' WHERE id = :id"
            ),
            {"id": r2["id"]},
        )

    with factory() as db:
        verdict_tampered = default_audit_service.verify_chain(db=db)
        assert verdict_tampered["valid"] is False
        assert verdict_tampered["broken_at_id"] == r2["id"]
        assert verdict_tampered["broken_trace_id"] == "trace-chain-2"


def test_aud_inv2_and_inv6_middleware_and_admin_endpoints(system_audit_db):
    """AUD-INV-2 & AUD-INV-6: AuditRequestMiddleware tự động ghi nhận hành động HTTP và liên kết cùng trace_id với đồ thị AI."""
    _, factory = system_audit_db

    app = FastAPI()
    app.add_middleware(AuditRequestMiddleware)

    def _override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[admin_user] = lambda: {"id": "admin-1", "role": "admin"}
    app.include_router(audit_endpoint.router, prefix="/api/v1/audit")

    @app.post("/api/v1/care-tracker/checkin/")
    def dummy_checkin():
        return {"status": "ok"}

    @app.get("/api/v1/patients/{patient_id}")
    def dummy_patient_view(patient_id: str):
        if patient_id == "FORBIDDEN-PATIENT":
            raise HTTPException(status_code=403, detail="Không có quyền truy cập hồ sơ này.")
        return {"patient_id": patient_id}

    client = TestClient(app)

    # 1. Gửi phiếu Check-in kèm X-Trace-Id
    res_checkin = client.post(
        "/api/v1/care-tracker/checkin/",
        headers={"X-Trace-Id": "trace-http-checkin-01"},
    )
    assert res_checkin.status_code == 200
    assert res_checkin.headers["X-Trace-Id"] == "trace-http-checkin-01"

    # 2. Truy cập bị từ chối 403 -> tự động ghi nhận AUTH.ACCESS_DENIED mức HIGH
    res_denied = client.get(
        "/api/v1/patients/FORBIDDEN-PATIENT",
        headers={"X-Trace-Id": "trace-http-denied-02"},
    )
    assert res_denied.status_code == 403

    # 3. Thực thi lượt hội thoại qua đồ thị LangGraph -> ghi đồng thời vào AgentActionLog, AuditLog và SystemAuditLog
    graph = build_aftercare_graph(
        profile_loader=lambda pid: {
            "patient_info": {"patient_id": pid, "full_name": "Trần Thị Mai"},
            "action_plan_rules": {"red_zone": "Xịt 4 nhát Ventolin và gọi 115."},
        },
        screener_fn=lambda text, prof: "RED_ZONE",
        retrieve_fn=lambda q, k: [],
        llm_caller=lambda p, m, history=None: "Không gọi",
    )
    chat_state = make_initial_state("BN-2026-ASTHMA-02", "Tôi bị tím môi và ngạt thở!")
    final_state = graph.invoke(chat_state)
    chat_trace_id = final_state["trace_id"]

    # 4. Kiểm tra GET /api/v1/audit/events
    res_events = client.get("/api/v1/audit/events")
    assert res_events.status_code == 200
    events_payload = res_events.json()
    assert events_payload["total"] == 3
    action_codes = {e["action_code"] for e in events_payload["events"]}
    assert "CLINICAL.PEF_CHECKIN_SUBMIT" in action_codes
    assert "AUTH.ACCESS_DENIED" in action_codes
    assert "AGENT.GRAPH_TURN_COMPLETED" in action_codes

    # 5. Kiểm tra GET /api/v1/audit/traces/{trace_id} hợp nhất cả 3 bảng
    res_trace = client.get(f"/api/v1/audit/traces/{chat_trace_id}")
    assert res_trace.status_code == 200
    trace_data = res_trace.json()
    assert trace_data["action"]["risk_level"] == "RED_ZONE"
    assert len(trace_data["events"]) >= 2
    assert len(trace_data["system_events"]) == 1
    assert trace_data["system_events"][0]["action_code"] == "AGENT.GRAPH_TURN_COMPLETED"

    # 6. Kiểm tra GET /api/v1/audit/verify-chain
    res_verify = client.get("/api/v1/audit/verify-chain")
    assert res_verify.status_code == 200
    assert res_verify.json()["valid"] is True
    assert res_verify.json()["checked_records"] == 3

