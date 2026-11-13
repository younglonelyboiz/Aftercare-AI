"""
KIỂM THỬ CÁC BẤT BIẾN THIẾT KẾ HÌNH THỨC (INV-1 ĐẾN INV-7) — [W07-T6.2].

Kiểm định từng bất biến kiến trúc đã quy định tại Mục 1 của tài liệu
`docs/Agent_Orchestration_Guardrails_Design.md`:
- INV-1 (Monotonic Risk): Mức độ nguy cơ không bao giờ bị hạ cấp trong một lượt xử lý.
- INV-2 (Zero-LLM Emergency): Luồng RED_ZONE và YELLOW_ZONE tuyệt đối không gọi LLM.
- INV-3 (Zero-Silent Escalation): Mọi sự kiện RED_ZONE, YELLOW_ZONE, POL-MED-STOP, POL-SELFHARM
  đều kích hoạt leo thang cảnh báo hoặc đẩy vào EscalationOutbox khi dịch vụ cảnh báo gặp sự cố.
- INV-4 (Fail-Closed Node Execution): Mọi lỗi runtime bất ngờ tại bất kỳ nút nào đều bị bắt bởi
  @safe_node và định tuyến về safe_fallback, tuyệt đối không rò rỉ stack trace.
- INV-5 (Evidence-Gated Generation): Truy vấn có 0 đoạn tài liệu vượt ngưỡng tau sẽ định tuyến
  sang no_evidence_response và gọi LLM đúng 0 lần.
- INV-6 (No PII Egress): PIIRedactor đảm bảo 0 trường định danh cá nhân (họ tên, mã bệnh nhân,
  số điện thoại, email, căn cước công dân, địa chỉ) xuất hiện trong prompt gửi tới LLM hoặc log kiểm toán.
- INV-7 (Complete Audit Trail): Mọi nhánh kết thúc trên đồ thị đều hội tụ qua finalize -> audit -> END
  và sinh đầy đủ trace_id, latency_ms, AgentActionLog và AuditLog.
"""
import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List
import pytest

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.guardrails.evidence_gate import EvidenceGate
from backend.app.guardrails.templates_vi import SAFE_FALLBACK_MESSAGE
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.nodes.escalate import EscalationOutboxDispatcher
from backend.app.orchestration.nodes.finalize_audit import get_cached_trace
from backend.app.orchestration.nodes.generate import make_generate_answer_node
from backend.app.orchestration.state import (
    RISK_ORDER,
    RiskDowngradeError,
    escalate_risk,
    make_initial_state,
)

PATIENT_PROFILE = {
    "patient_info": {
        "patient_id": "BN-2026-INV-99",
        "full_name": "Phạm Hoàng Minh Tuấn",
        "age": 54,
        "phone": "0912345678",
        "email": "phamhoangminhtuan@example.com",
        "cccd": "001072012345",
        "address": "Số 18 phố Giải Phóng, phường Phương Mai, quận Đống Đa",
    },
    "clinical_status": {
        "personal_best_pef": 400,
        "baseline_spo2": 97,
    },
    "current_medications": {
        "controller_med": "Symbicort 160/4.5mcg, hít 2 nhát x 2 lần/ngày.",
        "reliever_med": "Ventolin 100mcg, xịt 2 nhát khi khó thở.",
    },
    "action_plan_rules": {
        "yellow_zone": "Xịt 2 nhát Ventolin 100mcg và theo dõi sau 20 phút.",
        "red_zone": "Xịt ngay 4 nhát Ventolin 100mcg và gọi cấp cứu 115.",
    },
    "follow_up": {
        "hospital": "Bệnh viện Đại học Y Hà Nội",
    },
}

VALID_CHUNKS = [
    {
        "chunk_id": "GINA-2024-01",
        "parent_id": "DOC-GINA",
        "section_title": "Kỹ thuật hít thuốc và súc miệng",
        "citation": "QĐ 1851/QĐ-BYT, Mục 3.4",
        "safety_tier": "GREEN",
        "document_tag": "BYT_2020",
        "document_name": "Hướng dẫn chẩn đoán và điều trị Hen phế quản - Bộ Y tế",
        "pdf_page": 24,
        "content": "Súc miệng kỹ bằng nước sạch và nhổ đi sau khi hít thuốc chứa Corticosteroid.",
        "metadata": {"source": "QĐ 1851/QĐ-BYT", "section": "Mục 3.4"},
        "rerank_score": 0.89,
    }
]


def test_inv1_monotonic_risk_enforced_across_all_transitions():
    """INV-1: Kiểm định tính đơn điệu của risk_level trên toàn bộ không gian trạng thái."""
    levels = ["NORMAL", "YELLOW_ZONE", "RED_ZONE"]
    for current in levels:
        for target in levels:
            if RISK_ORDER[target] < RISK_ORDER[current]:
                with pytest.raises(RiskDowngradeError):
                    escalate_risk(current, target)
            else:
                result = escalate_risk(current, target)
                assert RISK_ORDER[result] >= RISK_ORDER[current]


def test_inv2_zero_llm_calls_in_red_yellow_and_locked_session():
    """INV-2: Luồng RED_ZONE, YELLOW_ZONE và phiên bị khóa RED_ZONE tuyệt đối không gọi LLM."""
    llm_calls: List[str] = []
    triage = TriageAgent()

    graph = build_aftercare_graph(
        profile_loader=lambda pid: PATIENT_PROFILE,
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: VALID_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
    )

    # 1. RED_ZONE
    s_red = graph.invoke(make_initial_state("BN-2026-INV-99", "Tôi tím môi và không thở được"))
    assert s_red["risk_level"] == "RED_ZONE"
    assert len(llm_calls) == 0

    # 2. YELLOW_ZONE
    s_yellow = graph.invoke(
        make_initial_state("BN-2026-INV-99", "Đêm qua tôi thức giấc nửa đêm vì ho và khò khè tăng")
    )
    assert s_yellow["risk_level"] == "YELLOW_ZONE"
    assert len(llm_calls) == 0

    # 3. Session Locked Red
    locked_profile = {
        **PATIENT_PROFILE,
        "active_alerts": [
            {"ticket_id": "AL-900", "priority": "P0_CRITICAL", "status": "OPEN"}
        ],
    }
    graph_locked = build_aftercare_graph(
        profile_loader=lambda pid: locked_profile,
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: VALID_CHUNKS,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
    )
    s_locked = graph_locked.invoke(
        make_initial_state("BN-2026-INV-99", "Cách vệ sinh bình xịt định liều như thế nào?")
    )
    assert s_locked["risk_level"] == "RED_ZONE"
    assert s_locked["session_locked_red"] is True
    assert len(llm_calls) == 0

    # 4. Gọi trực tiếp nút generate_answer khi risk_level != NORMAL phải ném RiskDowngradeError
    gen_node = make_generate_answer_node(
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời"
    )
    bad_state = make_initial_state("BN-2026-INV-99", "Câu hỏi")
    bad_state["risk_level"] = "RED_ZONE"
    with pytest.raises(RiskDowngradeError):
        gen_node(bad_state)
    assert len(llm_calls) == 0


def test_inv3_zero_silent_escalation_with_outbox_fallback(tmp_path):
    """INV-3: Mọi ca RED_ZONE, YELLOW_ZONE, POL-MED-STOP, POL-SELFHARM đều tạo vé cảnh báo
    hoặc lưu vào EscalationOutbox khi dịch vụ cảnh báo gặp lỗi."""
    triage = TriageAgent()
    created_tickets: List[Dict[str, Any]] = []

    class DummyEscalationService:
        def __init__(self, should_fail: bool = False):
            self.should_fail = should_fail

        async def create_or_escalate_ticket(self, **kwargs):
            if self.should_fail:
                raise RuntimeError("DB_CONNECTION_LOST")
            tid = f"TK-{len(created_tickets) + 1}"
            created_tickets.append({"id": tid, **kwargs})
            return SimpleNamespace(id=tid)

    dispatcher = EscalationOutboxDispatcher(
        session_factory=lambda: None,
        spool_path=tmp_path / "inv3_outbox.jsonl",
    )
    graph = build_aftercare_graph(
        profile_loader=lambda pid: PATIENT_PROFILE,
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: VALID_CHUNKS,
        llm_caller=lambda prompt, m, history=None: "Trả lời. QĐ 1851/QĐ-BYT",
    )

    cases = [
        ("Tôi bị tím tái môi và ngạt thở", "P0_CRITICAL", "CHAT_RED_FLAG_DETECTION"),
        ("Tôi bị thức giấc ban đêm và nặng ngực", "P1_HIGH", "CHAT_YELLOW_ZONE_ALERT"),
        ("Tôi thấy khỏe rồi nên tự ý bỏ thuốc Symbicort nhé", "P2_MEDIUM", "MEDICATION_NONADHERENCE_INTENT"),
        ("Tôi chán sống và muốn kết liễu cuộc đời", "P1_HIGH", "MENTAL_HEALTH_CONCERN"),
    ]
    service_ok = DummyEscalationService(should_fail=False)
    for msg, expected_prio, expected_alert_type in cases:
        final = graph.invoke(make_initial_state("BN-2026-INV-99", msg))
        risk = final["risk_level"]
        if risk == "RED_ZONE":
            prio = "P0_CRITICAL"
            atype = "CHAT_RED_FLAG_DETECTION"
        elif risk == "YELLOW_ZONE":
            prio = "P1_HIGH"
            atype = "CHAT_YELLOW_ZONE_ALERT"
        else:
            esc = final.get("policy_escalation")
            assert esc is not None
            prio = esc["priority"]
            atype = esc["alert_type"]

        assert prio == expected_prio
        assert atype == expected_alert_type
        ticket_id = asyncio.run(
            dispatcher.dispatch(
                service_ok,
                patient_id="BN-2026-INV-99",
                priority=prio,
                alert_type=atype,
                trigger_reason=msg,
                trace_id=final["trace_id"],
            )
        )
        assert ticket_id is not None

    assert len(created_tickets) == 4

    # Khi dịch vụ tạo vé lỗi -> phải lưu vào tệp spool dự phòng, không được mất dấu
    service_down = DummyEscalationService(should_fail=True)
    failed_tid = asyncio.run(
        dispatcher.dispatch(
            service_down,
            patient_id="BN-2026-INV-99",
            priority="P0_CRITICAL",
            alert_type="CHAT_RED_FLAG_DETECTION",
            trigger_reason="Tím môi khi DB sập",
            trace_id="trace-db-down",
        )
    )
    assert failed_tid is None
    assert (tmp_path / "inv3_outbox.jsonl").exists()
    spool_text = (tmp_path / "inv3_outbox.jsonl").read_text(encoding="utf-8")
    assert "CHAT_RED_FLAG_DETECTION" in spool_text


def test_inv4_fail_closed_node_execution_never_leaks_stack_trace():
    """INV-4: Bất kỳ nút nào phát sinh ngoại lệ runtime đều bị bắt bởi @safe_node và chuyển về safe_fallback."""

    def crashing_retriever(q: str, k: int):
        raise RuntimeError("FATAL_DATABASE_SOCKET_HANGUP_SECRET_PASSWORD_123")

    graph = build_aftercare_graph(
        profile_loader=lambda pid: PATIENT_PROFILE,
        screener_fn=lambda text, prof: "NORMAL",
        retrieve_fn=crashing_retriever,
        llm_caller=lambda prompt, m, history=None: "Không bao giờ tới đây",
    )
    final = graph.invoke(
        make_initial_state("BN-2026-INV-99", "Cách súc miệng sau khi dùng thuốc hít?")
    )
    assert final["degraded"] is True
    assert final["response_text"] == SAFE_FALLBACK_MESSAGE
    assert "FATAL_DATABASE_SOCKET_HANGUP" not in final["response_text"]
    assert any(ev["decision"] == "FALLBACK" for ev in final["guard_events"])


def test_inv5_evidence_gated_generation_blocks_unverified_queries():
    """INV-5: Truy vấn không có tài liệu vượt ngưỡng tau phải đi qua no_evidence_response với 0 lần gọi LLM."""
    llm_calls: List[str] = []
    low_score_chunks = [
        {
            "chunk_id": "LOW-01",
            "parent_id": "DOC-1",
            "section_title": "Mục khác",
            "citation": "QĐ 1851/QĐ-BYT",
            "safety_tier": "GREEN",
            "content": "Nội dung không liên quan.",
            "metadata": {"source": "QĐ 1851/QĐ-BYT"},
            "rerank_score": 0.12,
        }
    ]
    graph = build_aftercare_graph(
        profile_loader=lambda pid: PATIENT_PROFILE,
        screener_fn=lambda text, prof: "NORMAL",
        retrieve_fn=lambda q, k: low_score_chunks,
        llm_caller=lambda prompt, m, history=None: llm_calls.append(prompt) or "Trả lời",
        evidence_gate=EvidenceGate(min_score=0.35),
    )
    final = graph.invoke(
        make_initial_state("BN-2026-INV-99", "Bệnh tiểu đường thai kỳ ăn uống thế nào?")
    )
    assert final["evidence_ok"] is False
    assert len(llm_calls) == 0
    assert any(ev["rule_id"] == "EVIDENCE-GATE-REJECT" for ev in final["guard_events"])


def test_inv6_no_pii_egress_to_llm_or_audit_logs():
    """INV-6: Không rò rỉ thông tin định danh cá nhân (PII) sang LLM hoặc nhật ký kiểm toán."""
    captured_prompts: List[str] = []
    captured_histories: List[Any] = []

    def spy_llm(prompt: str, max_tokens: int, history=None) -> str:
        captured_prompts.append(prompt)
        captured_histories.append(history or [])
        return "Bác cần súc miệng sạch sau khi dùng Symbicort. Tài liệu tham khảo: QĐ 1851/QĐ-BYT, Mục 3.4"

    state = make_initial_state(
        "BN-2026-INV-99",
        "Tôi là Phạm Hoàng Minh Tuấn, số điện thoại 0912345678, CCCD 001072012345, hỏi cách súc miệng sau khi hít Symbicort?",
    )
    state["conversation_history"] = [
        {
            "role": "user",
            "content": "Địa chỉ nhà tôi ở Số 18 phố Giải Phóng, email phamhoangminhtuan@example.com",
        }
    ]

    graph = build_aftercare_graph(
        profile_loader=lambda pid: PATIENT_PROFILE,
        screener_fn=lambda text, prof: "NORMAL",
        retrieve_fn=lambda q, k: VALID_CHUNKS,
        llm_caller=spy_llm,
    )
    final = graph.invoke(state)
    assert len(captured_prompts) == 1
    sent_prompt = captured_prompts[0]
    sent_history_str = str(captured_histories[0])

    forbidden_pii = [
        "Phạm Hoàng Minh Tuấn",
        "BN-2026-INV-99",
        "0912345678",
        "001072012345",
        "phamhoangminhtuan@example.com",
        "Số 18 phố Giải Phóng",
    ]
    for pii_token in forbidden_pii:
        assert pii_token not in sent_prompt, f"Rò rỉ PII vào prompt LLM: {pii_token}"
        assert pii_token not in sent_history_str, f"Rò rỉ PII vào lịch sử LLM: {pii_token}"

    trace = get_cached_trace(final["trace_id"])
    assert trace is not None
    redacted_msg = trace["action"]["redacted_message"]
    for pii_token in forbidden_pii:
        assert pii_token not in redacted_msg, f"Rò rỉ PII vào bảng kiểm toán: {pii_token}"


def test_inv7_complete_audit_trail_across_all_graph_terminal_paths():
    """INV-7: Mọi đường đi kết thúc trên đồ thị đều hội tụ về finalize -> audit -> END."""
    triage = TriageAgent()

    # Kiểm tra 6 nhánh đại diện: RED, YELLOW, POLICY_BLOCK, NO_EVIDENCE, OUTPUT_BLOCK, NORMAL_PASS
    scenarios = [
        ("RED", "Tôi bị tím môi và không thở được", VALID_CHUNKS, "Hợp lệ QĐ 1851/QĐ-BYT"),
        ("YELLOW", "Đêm qua tôi thức giấc vì ho và nặng ngực", VALID_CHUNKS, "Hợp lệ QĐ 1851/QĐ-BYT"),
        ("POLICY_BLOCK", "Tôi tự ý ngưng thuốc Symbicort nhé", VALID_CHUNKS, "Hợp lệ QĐ 1851/QĐ-BYT"),
        ("NO_EVIDENCE", "Cách súc miệng sau khi hít thuốc?", [], "Hợp lệ QĐ 1851/QĐ-BYT"),
        (
            "OUTPUT_BLOCK",
            "Cách súc miệng sau khi hít thuốc?",
            VALID_CHUNKS,
            "Bác hãy uống ngay Prednisolone 500mg mỗi ngày.",
        ),
        (
            "NORMAL_PASS",
            "Cách súc miệng sau khi hít thuốc?",
            VALID_CHUNKS,
            "Bác cần súc miệng kỹ bằng nước sạch sau khi hít Symbicort. Nguồn: QĐ 1851/QĐ-BYT",
        ),
    ]

    for label, message, chunks, llm_reply in scenarios:
        graph = build_aftercare_graph(
            profile_loader=lambda pid: PATIENT_PROFILE,
            screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
            retrieve_fn=lambda q, k, c=chunks: c,
            llm_caller=lambda prompt, m, history=None, r=llm_reply: r,
        )
        final = graph.invoke(make_initial_state("BN-2026-INV-99", message))
        assert final.get("trace_id"), f"Thiếu trace_id ở nhánh {label}"
        assert final.get("response_text"), f"Thiếu response_text ở nhánh {label}"
        assert "audit" in final.get("latency_ms", {}), f"Thiếu nút audit ở nhánh {label}"
        recorded = get_cached_trace(final["trace_id"])
        assert recorded is not None, f"Không tìm thấy bản ghi kiểm toán cho nhánh {label}"
        assert len(recorded["events"]) >= 2, f"Thiếu chuỗi sự kiện guard_events cho nhánh {label}"
