"""
KIỂM THỬ GIAI ĐOẠN 5 — HÀNG ĐỢI LEO THANG OUTBOX, NHẬT KÝ KIỂM TOÁN BẤT BIẾN VÀ ĐO LƯỜNG QUAN SÁT (W07-PHASE5)

T5.1  Kiểm tra `AlertTicketDTO` tự động gán `source_channel="CHATBOT"`, `alert_type_label` và nhãn giao diện `NurseCommandCenter.jsx`
T5.2  Kiểm tra `EscalationOutboxDispatcher` không làm mất vé khi cơ sở dữ liệu/dịch vụ gián đoạn rồi phục hồi (`flush_pending`)
T5.3  Kiểm tra bảng `agent_actions_log` và `audit_logs` lưu 1 bản ghi action + N bản ghi event cùng `trace_id`, ẩn danh PII và cưỡng chế append-only (`ImmutableAuditRecordError`)
T5.4  Kiểm tra endpoint chỉ đọc cho quản trị viên `GET /api/v1/audit/traces/{trace_id}` (chặn quyền thường, từ chối PUT/DELETE)
T5.5  Kiểm tra `OrchestrationMetricsCollector` tính phân vị độ trễ `P50`/`P95` theo từng nút và xuất `Evidence/W07/metrics.json`
"""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.v1.endpoints import audit as audit_endpoint
from backend.app.core.database import get_db
from backend.app.core.security import admin_user
from backend.app.db.migrate_audit_tables import migrate_audit_tables
from backend.app.models.audit import (
    AgentActionLog,
    AuditLog,
    EscalationOutbox,
    ImmutableAuditRecordError,
)
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.nodes.escalate import EscalationOutboxDispatcher
from backend.app.orchestration.nodes.finalize_audit import (
    metrics_collector,
    set_audit_session_factory,
)
from backend.app.orchestration.state import make_initial_state
from backend.app.schemas.care_tracker import AlertTicketDTO

SAMPLE_PROFILE = {
    "patient_info": {
        "patient_id": "BN-2026-ASTHMA-02",
        "full_name": "Trần Thị Mai",
        "age": 61,
        "phone": "0988777666",
    },
    "clinical_status": {"personal_best_pef": 280, "baseline_spo2": 95},
    "current_medications": {
        "controller_med": "Symbicort 160/4.5mcg",
        "reliever_med": "Ventolin 100mcg",
    },
    "action_plan_rules": {
        "yellow_zone": "Xịt 2 nhát Ventolin 100mcg và theo dõi sau 20 phút.",
        "red_zone": "Xịt ngay 4 nhát Ventolin và gọi cấp cứu 115.",
    },
    "follow_up": {"hospital": "Bệnh viện Bạch Mai"},
}


@pytest.fixture
def audit_db(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    migrate_audit_tables(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    set_audit_session_factory(factory)
    yield factory, tmp_path
    set_audit_session_factory(None)


# ---------------------------------------------------------------------------
# T5.1 — Nhãn nguồn Chatbot trong AlertTicketDTO & NurseCommandCenter.jsx
# ---------------------------------------------------------------------------
def test_t51_alert_ticket_dto_populates_chatbot_channel_and_ui_badge():
    chat_ticket = AlertTicketDTO(
        id="t-chat-01",
        patient_id="BN-2026-ASTHMA-02",
        priority="P0_CRITICAL",
        alert_type="CHAT_RED_FLAG_DETECTION",
        trigger_reason="Phát hiện qua Chatbot: Khó thở nặng, tím môi",
        clinical_data={"source": "CHAT"},
        status="OPEN",
        created_at="2026-11-13T10:00:00",
    )
    assert chat_ticket.source_channel == "CHATBOT"
    assert "Chatbot" in (chat_ticket.alert_type_label or "")

    med_stop_ticket = AlertTicketDTO(
        id="t-chat-02",
        patient_id="BN-2026-ASTHMA-01",
        priority="P2_MEDIUM",
        alert_type="MEDICATION_NONADHERENCE_INTENT",
        trigger_reason="Phát hiện qua Chatbot (quy tắc POL-MED-STOP): Tự ý bỏ thuốc",
        status="OPEN",
        created_at="2026-11-13T10:05:00",
    )
    assert med_stop_ticket.source_channel == "CHATBOT"
    assert "ngưng thuốc" in (med_stop_ticket.alert_type_label or "")

    checkin_ticket = AlertTicketDTO(
        id="t-chk-01",
        patient_id="BN-2026-ASTHMA-02",
        priority="P0_CRITICAL",
        alert_type="RED_ZONE_DETECTION",
        trigger_reason="PEF < 60%",
        status="OPEN",
        created_at="2026-11-13T10:10:00",
    )
    assert checkin_ticket.source_channel == "CHECKIN"

    # Kiểm tra mã nguồn giao diện NurseCommandCenter.jsx và LiveAlertBanner.jsx có hiển thị "Nguồn: Chatbot"
    nurse_ui = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "src"
        / "components"
        / "Nurse"
        / "NurseCommandCenter.jsx"
    ).read_text(encoding="utf-8")
    banner_ui = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "src"
        / "components"
        / "Nurse"
        / "LiveAlertBanner.jsx"
    ).read_text(encoding="utf-8")
    assert "Nguồn: Chatbot" in nurse_ui
    assert "Nguồn: Chatbot" in banner_ui


# ---------------------------------------------------------------------------
# T5.2 — Escalation Outbox Pattern (không mất vé khi DB/dịch vụ gián đoạn)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t52_escalation_outbox_recovers_tickets_after_outage(audit_db):
    factory, tmp_path = audit_db
    spool_file = tmp_path / "outbox_spool.jsonl"
    dispatcher = EscalationOutboxDispatcher(
        session_factory=factory, spool_path=spool_file
    )

    class FlakyEscalationService:
        def __init__(self):
            self.down = True
            self.created = []

        async def create_or_escalate_ticket(self, **kwargs):
            if self.down:
                raise ConnectionError("Database connection refused (simulated 30s outage)")
            self.created.append(kwargs)
            return SimpleNamespace(id=f"recovered-ticket-{len(self.created)}")

    svc = FlakyEscalationService()

    # 1. Khi dịch vụ đang sập: dispatch không ném lỗi (non-blocking), trả về None và lưu vào bảng escalation_outbox
    res_during_outage = await dispatcher.dispatch(
        svc,
        patient_id="BN-2026-ASTHMA-02",
        priority="P0_CRITICAL",
        alert_type="CHAT_RED_FLAG_DETECTION",
        trigger_reason="Phát hiện qua Chatbot: Không thở được, tím môi",
        trace_id="trace-outage-01",
    )
    assert res_during_outage is None
    assert len(svc.created) == 0

    with factory() as db:
        pending = db.scalars(select(EscalationOutbox)).all()
        assert len(pending) == 1
        assert pending[0].status == "PENDING"
        assert pending[0].priority == "P0_CRITICAL"

    # 2. Sau khi dịch vụ phục hồi: gọi flush_pending() -> vé được tạo đầy đủ, trạng thái chuyển thành SENT
    svc.down = False
    recovered_ids = await dispatcher.flush_pending(svc)
    assert recovered_ids == ["recovered-ticket-1"]
    assert len(svc.created) == 1
    assert svc.created[0]["patient_id"] == "BN-2026-ASTHMA-02"

    with factory() as db:
        row = db.scalar(select(EscalationOutbox))
        assert row.status == "SENT"
        assert row.ticket_id == "recovered-ticket-1"


# ---------------------------------------------------------------------------
# T5.3 — Bảng `agent_actions_log` và `audit_logs` (Append-only & PII Redacted)
# ---------------------------------------------------------------------------
def test_t53_audit_tables_persist_redacted_trace_and_enforce_append_only(audit_db):
    factory, _ = audit_db
    graph = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=lambda t, p: SimpleNamespace(
            risk_level="NORMAL", matched_flags=[], matched_reasons=[]
        ),
        retrieve_fn=lambda q, k: [
            {
                "chunk_id": "CHK-01",
                "section_title": "Súc miệng sau khi dùng ICS",
                "citation": "QĐ 1851/QĐ-BYT, Mục 2.7.2",
                "safety_tier": "KHO_2",
                "content": "Súc miệng sạch bằng nước sau khi hít corticoid.",
                "rerank_score": 0.92,
                "similarity_score": 0.92,
            }
        ],
        llm_caller=lambda prompt, m, history=None: "Bác cần súc miệng sạch sau khi hít Symbicort.",
    )

    raw_msg = "Tôi là Trần Thị Mai (SĐT 0988777666, mã BN-2026-ASTHMA-02), sau khi hít Symbicort có cần súc miệng không?"
    final = graph.invoke(make_initial_state("BN-2026-ASTHMA-02", raw_msg))
    trace_id = final["trace_id"]

    with factory() as db:
        action = db.scalar(
            select(AgentActionLog).where(AgentActionLog.trace_id == trace_id)
        )
        events = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.trace_id == trace_id)
                .order_by(AuditLog.sequence)
            ).all()
        )

        assert action is not None
        assert len(events) == len(final["guard_events"])
        assert len(events) >= 4
        # Kiểm tra mã băm SHA-256 khớp bản gốc nhưng văn bản lưu DB đã ẩn danh PII hoàn toàn
        assert (
            action.message_sha256
            == hashlib.sha256(raw_msg.encode("utf-8")).hexdigest()
        )
        assert "Trần Thị Mai" not in action.redacted_message
        assert "0988777666" not in action.redacted_message
        assert "BN-2026-ASTHMA-02" not in action.redacted_message
        assert "Người bệnh" in action.redacted_message

        # Kiểm tra cưỡng chế Append-only: cố tình sửa hoặc xóa bản ghi kiểm toán phải ném ImmutableAuditRecordError
        action.risk_level = "RED_ZONE"
        with pytest.raises(ImmutableAuditRecordError):
            db.commit()
        db.rollback()

        ev0 = db.scalar(select(AuditLog).where(AuditLog.trace_id == trace_id))
        db.delete(ev0)
        with pytest.raises(ImmutableAuditRecordError):
            db.commit()
        db.rollback()


# ---------------------------------------------------------------------------
# T5.4 — Endpoint chỉ đọc `GET /api/v1/audit/traces/{trace_id}`
# ---------------------------------------------------------------------------
def test_t54_admin_read_only_audit_trace_endpoint(audit_db):
    factory, _ = audit_db
    graph = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=lambda t, p: SimpleNamespace(
            risk_level="RED_ZONE",
            matched_flags=["red_cyanosis"],
            matched_reasons=["Tím môi, khó thở dữ dội"],
        ),
        retrieve_fn=lambda q, k: [],
        llm_caller=lambda prompt, m, history=None: "Không gọi",
    )
    final = graph.invoke(
        make_initial_state("BN-2026-ASTHMA-02", "Tôi bị tím môi và không thở được")
    )
    trace_id = final["trace_id"]

    app = FastAPI()
    app.include_router(audit_endpoint.router, prefix="/api/v1/audit")

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    # 1. Khi chưa đăng nhập admin -> bị chặn 401
    unauth_client = TestClient(app)
    assert unauth_client.get(f"/api/v1/audit/traces/{trace_id}").status_code == 401

    # 2. Khi có quyền admin -> đọc được đầy đủ action + events theo thứ tự bước đi qua đồ thị
    app.dependency_overrides[admin_user] = lambda: SimpleNamespace(
        id="admin-1", role="admin"
    )
    admin_client = TestClient(app)
    res = admin_client.get(f"/api/v1/audit/traces/{trace_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["trace_id"] == trace_id
    assert body["action"]["risk_level"] == "RED_ZONE"
    assert len(body["events"]) >= 2
    assert [e["sequence"] for e in body["events"]] == list(
        range(1, len(body["events"]) + 1)
    )

    # 3. Không tồn tại phương thức PUT hoặc DELETE (chỉ đọc)
    assert admin_client.delete(f"/api/v1/audit/traces/{trace_id}").status_code == 405
    assert (
        admin_client.put(f"/api/v1/audit/traces/{trace_id}", json={}).status_code == 405
    )


# ---------------------------------------------------------------------------
# T5.5 — Thu thập metrics P50/P95 theo từng nút & xuất `Evidence/W07/metrics.json`
# ---------------------------------------------------------------------------
def test_t55_metrics_collector_computes_p50_p95_and_exports_json(audit_db):
    metrics_collector.reset()

    graph_normal = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=lambda t, p: SimpleNamespace(
            risk_level="NORMAL", matched_flags=[], matched_reasons=[]
        ),
        retrieve_fn=lambda q, k: [
            {
                "chunk_id": "CHK-01",
                "section_title": "Súc miệng",
                "citation": "QĐ 1851/QĐ-BYT",
                "safety_tier": "KHO_2",
                "content": "Súc miệng bằng nước sạch sau khi hít thuốc.",
                "rerank_score": 0.91,
                "similarity_score": 0.91,
            }
        ],
        llm_caller=lambda prompt, m, history=None: "Cần súc miệng sạch sau khi hít Symbicort.",
    )
    graph_red = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=lambda t, p: SimpleNamespace(
            risk_level="RED_ZONE",
            matched_flags=["red_speech"],
            matched_reasons=["Nói từng từ"],
        ),
        retrieve_fn=lambda q, k: [],
        llm_caller=lambda prompt, m, history=None: "Không gọi",
    )

    for _ in range(3):
        graph_normal.invoke(
            make_initial_state("BN-2026-ASTHMA-02", "Cách súc miệng sau khi hít thuốc?")
        )
    for _ in range(2):
        graph_red.invoke(
            make_initial_state("BN-2026-ASTHMA-02", "Tôi khó thở quá không nói thành câu")
        )
    # 1 lượt bị chặn bởi Policy Guard
    graph_normal.invoke(
        make_initial_state("BN-2026-ASTHMA-02", "Tôi tự ngưng thuốc Symbicort luôn nhé")
    )

    out_path = metrics_collector.export_json()
    assert out_path.exists()

    snap = metrics_collector.snapshot()
    assert snap["total_traces"] == 6
    assert snap["risk_level_total"]["NORMAL"] == 4
    assert snap["risk_level_total"]["RED_ZONE"] == 2
    assert snap["guard_block_total"].get("POL-MED-STOP", 0) >= 1
    assert "safety_triage" in snap["node_latency_ms"]
    assert "p50_ms" in snap["node_latency_ms"]["safety_triage"]
    assert "p95_ms" in snap["node_latency_ms"]["safety_triage"]
    assert snap["end_to_end_latency_by_risk_ms"]["RED_ZONE"]["p95_ms"] < 100

