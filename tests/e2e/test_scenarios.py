"""
KIỂM THỬ TÍCH HỢP ĐẦU-CUỐI (END-TO-END) 4 KỊCH BẢN LÂM SÀNG TRỌNG YẾU — [W07-T6.3].

Kiểm định toàn trình 4 kịch bản thực tế từ đầu vào của bệnh nhân qua đồ thị điều phối
`build_aftercare_graph`, bộ tạo vé cảnh báo `EscalationOutboxDispatcher` và bảng kiểm toán
bất biến `AgentActionLog` / `AuditLog`:
- Kịch bản A (Vùng Xanh — Tư vấn giáo dục sức khỏe có căn cứ): Hỏi cách súc miệng sau khi hít
  Symbicort -> vượt qua L0-L5 -> trả lời có trích dẫn Bộ Y tế và miễn trừ trách nhiệm, 0 vé cảnh báo.
- Kịch bản B (Vùng Đỏ — Cấp cứu hô hấp + Khóa phiên Vùng Đỏ): Báo khó thở không nói hết câu,
  tím môi -> trả hướng dẫn cấp cứu (115), tạo vé P0_CRITICAL (CHAT_RED_FLAG_DETECTION), 0 lần gọi LLM;
  câu hỏi tiếp theo trong cùng phiên ("Cách rửa buồng đệm?") vẫn bị khóa cứng ở RED_ZONE cho tới khi
  điều dưỡng đóng vé P0_CRITICAL.
- Kịch bản C (Vùng Vàng — Cơn hen trở nặng): Báo thức giấc nửa đêm vì ho, khò khè tăng -> trả kế hoạch
  hành động Vùng Vàng (theo dõi sau 20 phút), tạo vé P1_HIGH (CHAT_YELLOW_ZONE_ALERT), 0 lần gọi LLM.
- Kịch bản D (Vi phạm chính sách — Ý định tự ý ngưng thuốc kiểm soát): Báo muốn tự ngưng Symbicort
  vì thấy khỏe -> chặn tại L2 (POL-MED-STOP), trả thông điệp từ chối kèm trích dẫn Bộ Y tế, tạo vé
  P2_MEDIUM (MEDICATION_NONADHERENCE_INTENT), 0 lần gọi LLM.
"""
import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.db.migrate_audit_tables import migrate_audit_tables
from backend.app.models.audit import AgentActionLog, AuditLog
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.nodes.escalate import EscalationOutboxDispatcher
from backend.app.orchestration.nodes.finalize_audit import set_audit_session_factory
from backend.app.orchestration.state import make_initial_state
from backend.app.schemas.care_tracker import AlertTicketDTO

BASE_PROFILE = {
    "patient_info": {
        "patient_id": "BN-2026-E2E-01",
        "full_name": "Nguyễn Thị Thanh Hương",
        "age": 58,
        "phone": "0903112233",
    },
    "clinical_status": {
        "personal_best_pef": 320,
        "baseline_spo2": 96,
    },
    "current_medications": {
        "controller_med": "Symbicort 160/4.5mcg, hít 2 nhát x 2 lần/ngày.",
        "reliever_med": "Ventolin 100mcg, xịt 2 nhát khi khó thở.",
    },
    "action_plan_rules": {
        "yellow_zone": "Xịt 2 nhát Ventolin 100mcg và đánh giá lại sau 20 phút.",
        "red_zone": "Xịt ngay 4 nhát Ventolin qua buồng đệm và gọi cấp cứu 115.",
    },
    "follow_up": {
        "hospital": "Bệnh viện Bạch Mai",
    },
    "active_alerts": [],
}

E2E_CHUNKS = [
    {
        "chunk_id": "BYT-2020-3.4",
        "parent_id": "DOC-BYT",
        "section_title": "Hướng dẫn kỹ thuật sử dụng bình hít Corticosteroid",
        "citation": "QĐ 1851/QĐ-BYT, Mục 3.4",
        "safety_tier": "GREEN",
        "document_tag": "BYT_2020",
        "document_name": "Hướng dẫn chẩn đoán và điều trị Hen phế quản - Bộ Y tế",
        "pdf_page": 24,
        "content": (
            "Sau khi hít thuốc kiểm soát chứa Corticosteroid (như Symbicort hoặc Seretide), "
            "người bệnh bắt buộc phải súc miệng kỹ bằng nước sạch rồi nhổ đi để phòng ngừa "
            "nấm họng và khàn tiếng."
        ),
        "metadata": {"source": "QĐ 1851/QĐ-BYT", "section": "Mục 3.4"},
        "rerank_score": 0.92,
    }
]


@pytest.fixture
def e2e_env(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    migrate_audit_tables(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    set_audit_session_factory(factory)

    tickets: List[AlertTicketDTO] = []

    class InMemoryEscalationService:
        async def create_or_escalate_ticket(
            self,
            *,
            patient_id: str,
            priority: str,
            alert_type: str,
            trigger_reason: str,
            patient_name: str = None,
            clinical_data: Dict[str, Any] = None,
        ):
            tid = f"AL-E2E-{len(tickets) + 1:02d}"
            dto = AlertTicketDTO(
                id=tid,
                patient_id=patient_id,
                patient_name=patient_name,
                priority=priority,
                alert_type=alert_type,
                trigger_reason=trigger_reason,
                clinical_data=clinical_data or {},
                status="OPEN",
                created_at="2026-11-13T12:00:00",
            )
            tickets.append(dto)
            return SimpleNamespace(id=tid, dto=dto)

    dispatcher = EscalationOutboxDispatcher(
        session_factory=factory,
        spool_path=tmp_path / "e2e_outbox.jsonl",
    )
    yield factory, tickets, InMemoryEscalationService(), dispatcher
    set_audit_session_factory(None)


def test_scenario_a_green_zone_grounded_education(e2e_env):
    """Kịch bản A: Câu hỏi hợp lệ Vùng Xanh -> trả lời có trích dẫn Bộ Y tế và miễn trừ trách nhiệm, 0 vé cảnh báo."""
    factory, tickets, _, _ = e2e_env
    triage = TriageAgent()
    llm_calls: List[str] = []

    graph = build_aftercare_graph(
        profile_loader=lambda pid: dict(BASE_PROFILE),
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: E2E_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt)
        or "Sau khi hít thuốc kiểm soát chứa Corticosteroid, Bác cần súc miệng kỹ bằng nước sạch rồi nhổ đi để ngừa nấm họng.",
    )

    final = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Tại sao tôi phải súc miệng sau khi hít thuốc ngừa cơn?",
        )
    )

    assert final["risk_level"] == "NORMAL"
    assert final["policy_decision"] == "ALLOW"
    assert final["evidence_ok"] is True
    assert final["degraded"] is False
    assert len(llm_calls) == 1
    assert "QĐ 1851/QĐ-BYT" in final["response_text"]
    assert "Lưu ý" in final["response_text"] or "không thay thế" in final["response_text"]
    assert len(tickets) == 0

    with factory() as db:
        action = db.scalar(
            select(AgentActionLog).where(AgentActionLog.trace_id == final["trace_id"])
        )
        assert action is not None
        assert action.risk_level == "NORMAL"
        assert "Nguyễn Thị Thanh Hương" not in action.redacted_message


def test_scenario_b_red_zone_emergency_and_session_lock(e2e_env):
    """Kịch bản B: Cờ đỏ cấp cứu -> 0 LLM, tạo vé P0_CRITICAL, khóa cứng phiên ở RED_ZONE cho tới khi đóng vé."""
    factory, tickets, esc_service, dispatcher = e2e_env
    triage = TriageAgent()
    llm_calls: List[str] = []
    live_profile = dict(BASE_PROFILE, active_alerts=[])

    graph = build_aftercare_graph(
        profile_loader=lambda pid: live_profile,
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: E2E_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
    )

    # Lượt 1: Bệnh nhân báo triệu chứng cờ đỏ
    turn1 = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Cứu tôi với, tôi tím môi và khó thở dữ dội chỉ nói được từng từ một!",
        )
    )
    assert turn1["risk_level"] == "RED_ZONE"
    assert len(llm_calls) == 0
    assert "115" in turn1["response_text"]

    tid = asyncio.run(
        dispatcher.dispatch(
            esc_service,
            patient_id="BN-2026-E2E-01",
            priority="P0_CRITICAL",
            alert_type="CHAT_RED_FLAG_DETECTION",
            trigger_reason="Khó thở dữ dội, tím môi",
            trace_id=turn1["trace_id"],
        )
    )
    assert tid is not None
    assert len(tickets) == 1
    assert tickets[0].priority == "P0_CRITICAL"
    assert tickets[0].source_channel == "CHATBOT"

    # Mô phỏng vé P0_CRITICAL đang OPEN trong hồ sơ bệnh nhân
    live_profile["active_alerts"] = [
        {"ticket_id": tid, "priority": "P0_CRITICAL", "status": "OPEN"}
    ]

    # Lượt 2: Bệnh nhân hỏi câu thông thường khi vé P0 chưa được xử lý -> vẫn bị khóa ở RED_ZONE
    turn2 = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Cho tôi hỏi cách rửa bình xịt định liều bằng nước ấm?",
        )
    )
    assert turn2["risk_level"] == "RED_ZONE"
    assert turn2["session_locked_red"] is True
    assert len(llm_calls) == 0
    assert "115" in turn2["response_text"]

    # Lượt 3: Điều dưỡng đã xử lý và đóng vé P0_CRITICAL -> mở khóa phiên, trả lời bình thường
    live_profile["active_alerts"] = [
        {"ticket_id": tid, "priority": "P0_CRITICAL", "status": "RESOLVED"}
    ]
    turn3 = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Tại sao phải súc miệng sau khi dùng thuốc ngừa cơn?",
        )
    )
    assert turn3["risk_level"] == "NORMAL"
    assert turn3["session_locked_red"] is False
    assert len(llm_calls) == 1


def test_scenario_c_yellow_zone_exacerbation_action_plan(e2e_env):
    """Kịch bản C: Dấu hiệu hen trở nặng Vùng Vàng -> trả kế hoạch hành động, tạo vé P1_HIGH, 0 lần gọi LLM."""
    factory, tickets, esc_service, dispatcher = e2e_env
    triage = TriageAgent()
    llm_calls: List[str] = []

    graph = build_aftercare_graph(
        profile_loader=lambda pid: dict(BASE_PROFILE),
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: E2E_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
    )

    final = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Hai đêm nay tôi hay thức giấc nửa đêm vì ho, sáng nay thấy nặng ngực và khò khè tăng",
        )
    )
    assert final["risk_level"] == "YELLOW_ZONE"
    assert len(llm_calls) == 0
    assert "20 phút" in final["response_text"]

    tid = asyncio.run(
        dispatcher.dispatch(
            esc_service,
            patient_id="BN-2026-E2E-01",
            priority="P1_HIGH",
            alert_type="CHAT_YELLOW_ZONE_ALERT",
            trigger_reason="Thức giấc nửa đêm vì ho, nặng ngực, khò khè tăng",
            trace_id=final["trace_id"],
        )
    )
    assert tid is not None
    assert len(tickets) == 1
    assert tickets[0].priority == "P1_HIGH"
    assert tickets[0].alert_type == "CHAT_YELLOW_ZONE_ALERT"


def test_scenario_d_policy_violation_medication_nonadherence(e2e_env):
    """Kịch bản D: Bệnh nhân muốn tự ý bỏ thuốc kiểm soát -> chặn tại L2 (POL-MED-STOP), tạo vé P2_MEDIUM, 0 LLM."""
    factory, tickets, esc_service, dispatcher = e2e_env
    triage = TriageAgent()
    llm_calls: List[str] = []

    graph = build_aftercare_graph(
        profile_loader=lambda pid: dict(BASE_PROFILE),
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: E2E_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
    )

    final = graph.invoke(
        make_initial_state(
            "BN-2026-E2E-01",
            "Tôi thấy hết khó thở rồi nên định tự ý ngưng thuốc Symbicort luôn nhé?",
        )
    )
    assert final["risk_level"] == "NORMAL"
    assert final["policy_decision"] == "BLOCK"
    assert final["policy_rule_id"] == "POL-MED-STOP"
    assert len(llm_calls) == 0
    assert "KHÔNG được tự ý ngưng" in final["response_text"]

    esc = final["policy_escalation"]
    assert esc is not None
    tid = asyncio.run(
        dispatcher.dispatch(
            esc_service,
            patient_id="BN-2026-E2E-01",
            priority=esc["priority"],
            alert_type=esc["alert_type"],
            trigger_reason="Bệnh nhân định tự ý ngưng Symbicort",
            trace_id=final["trace_id"],
        )
    )
    assert tid is not None
    assert len(tickets) == 1
    assert tickets[0].priority == "P2_MEDIUM"
    assert tickets[0].alert_type == "MEDICATION_NONADHERENCE_INTENT"

    with factory() as db:
        events = db.scalars(
            select(AuditLog)
            .where(AuditLog.trace_id == final["trace_id"])
            .order_by(AuditLog.sequence)
        ).all()
        assert any(ev.rule_id == "POL-MED-STOP" and ev.decision == "BLOCKED" for ev in events)

