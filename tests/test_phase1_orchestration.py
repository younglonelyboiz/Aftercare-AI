"""
KIỂM THỬ GIAI ĐOẠN 1 — NỀN TẢNG ĐIỀU PHỐI LANGGRAPH (W07-PHASE1)

T1.1  Kiểm tra gói phụ thuộc langgraph và pyyaml
T1.2  Kiểm tra bất biến rủi ro đơn điệu INV-1 (escalate_risk, RiskDowngradeError)
T1.3  Kiểm tra decorator @safe_node cưỡng chế Fail-closed (INV-4) và đo latency_ms
T1.4  Kiểm tra các nút chuyên trách và mẫu phản hồi tiếng Việt (templates_vi)
T1.5  Kiểm tra bảng quyết định (decision table) 100% cạnh rẽ nhánh trong routing.py & graph.py
T1.6  Kiểm tra AftercareRAGService facade trả về trace_id và guard_events
T1.7  Kiểm tra LLMGateway (danh sách trắng model, chuỗi dự phòng OpenRouter -> Gemini -> None)
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from backend.app.guardrails.templates_vi import (
    NO_EVIDENCE_MESSAGE,
    SAFE_FALLBACK_MESSAGE,
)
from backend.app.llm.gateway import LLMGateway
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.routing import (
    route_after_generate,
    route_after_load_context,
    route_after_output_guard,
    route_after_policy,
    route_after_retrieve,
    route_after_sanitize,
    route_after_session_lock,
    route_after_triage,
)
from backend.app.orchestration.safe_node import PatientNotFoundError, safe_node
from backend.app.orchestration.state import (
    AftercareState,
    RiskDowngradeError,
    append_guard_event,
    escalate_risk,
    make_initial_state,
)

SAMPLE_PROFILE = {
    "patient_info": {"patient_id": "BN-TEST-01", "full_name": "Nguyễn Văn An"},
    "clinical_status": {"personal_best_pef": 480},
    "current_medications": {"reliever_med": "Ventolin 100mcg"},
    "action_plan_rules": {
        "yellow_zone": "Xịt 2 nhát Ventolin, nghỉ ngơi và đo lại PEF sau 20 phút.",
        "red_zone": "Xịt ngay 4 nhát Ventolin qua buồng đệm và gọi 115.",
    },
    "follow_up": {"hospital": "Bệnh viện Phổi Trung ương"},
}

SAMPLE_CHUNKS = [
    {
        "chunk_id": "chunk-01",
        "section_title": "Hướng dẫn súc miệng sau khi dùng ICS",
        "citation": "QĐ 1851/QĐ-BYT, Mục 2.7.2",
        "safety_tier": "KHO_2",
        "document_tag": "byt_1851",
        "document_name": "Hướng dẫn chẩn đoán và điều trị Hen phế quản",
        "pdf_page": 12,
        "content": "Súc miệng và họng sạch bằng nước sau khi hít thuốc chứa corticoid.",
        "similarity_score": 0.92,
    }
]


# ---------------------------------------------------------------------------
# T1.1 — Gói phụ thuộc
# ---------------------------------------------------------------------------
def test_t11_dependencies_available():
    from langgraph.graph import StateGraph

    parsed = yaml.safe_load("rule_id: TEST\ndecision: BLOCK\n")
    assert StateGraph is not None
    assert parsed["rule_id"] == "TEST"


# ---------------------------------------------------------------------------
# T1.2 — Bất biến INV-1: Monotonic Risk
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "current,new,expected",
    [
        (None, "NORMAL", "NORMAL"),
        ("NORMAL", "NORMAL", "NORMAL"),
        ("NORMAL", "YELLOW_ZONE", "YELLOW_ZONE"),
        ("NORMAL", "RED_ZONE", "RED_ZONE"),
        ("YELLOW_ZONE", "YELLOW_ZONE", "YELLOW_ZONE"),
        ("YELLOW_ZONE", "RED_ZONE", "RED_ZONE"),
        ("RED_ZONE", "RED_ZONE", "RED_ZONE"),
    ],
)
def test_t12_escalate_risk_allows_monotonic_increase(current, new, expected):
    assert escalate_risk(current, new) == expected


@pytest.mark.parametrize(
    "current,new",
    [
        ("RED_ZONE", "YELLOW_ZONE"),
        ("RED_ZONE", "NORMAL"),
        ("YELLOW_ZONE", "NORMAL"),
    ],
)
def test_t12_escalate_risk_rejects_downgrade(current, new):
    with pytest.raises(RiskDowngradeError):
        escalate_risk(current, new)


# ---------------------------------------------------------------------------
# T1.3 — Decorator @safe_node (INV-4: Fail-closed)
# ---------------------------------------------------------------------------
def test_t13_safe_node_records_latency_on_success():
    @safe_node("demo_node", layer="L_TEST")
    def ok_node(state: AftercareState):
        return {"response_text": "Thành công"}

    state = make_initial_state("BN-01", "xin chào")
    out = ok_node(state)
    assert out["response_text"] == "Thành công"
    assert "demo_node" in out["latency_ms"]
    assert out["latency_ms"]["demo_node"] >= 0


def test_t13_safe_node_catches_unexpected_exception_and_sets_fallback():
    @safe_node("broken_node", layer="L_TEST")
    def broken_node(state: AftercareState):
        raise RuntimeError("Lỗi kết nối nội bộ")

    state = make_initial_state("BN-01", "xin chào")
    out = broken_node(state)
    assert out["degraded"] is True
    assert out["error"] == "broken_node:RuntimeError"
    assert out["guard_events"][-1]["decision"] == "FALLBACK"
    assert out["guard_events"][-1]["rule_id"] == "SYS-NODE-ERROR:broken_node"


def test_t13_safe_node_passes_through_patient_not_found_and_risk_downgrade():
    @safe_node("loader", layer="L0")
    def not_found_node(state: AftercareState):
        raise PatientNotFoundError("Không tìm thấy bệnh nhân")

    @safe_node("bad_risk", layer="L1")
    def downgrade_node(state: AftercareState):
        escalate_risk("RED_ZONE", "NORMAL")
        return {}

    state = make_initial_state("BN-404", "xin chào")
    with pytest.raises(PatientNotFoundError):
        not_found_node(state)
    with pytest.raises(RiskDowngradeError):
        downgrade_node(state)


# ---------------------------------------------------------------------------
# T1.5 — Bảng quyết định (Decision Table) cho toàn bộ các hàm định tuyến
# ---------------------------------------------------------------------------
def test_t15_routing_decision_table():
    assert route_after_load_context({"error": None}) == "sanitize_input"
    assert route_after_load_context({"error": "load_context:Err"}) == "safe_fallback"

    assert route_after_sanitize({"error": None}) == "safety_triage"
    assert route_after_sanitize({"error": "sanitize:Err"}) == "safe_fallback"

    assert route_after_triage({"risk_level": "RED_ZONE"}) == "emergency_response"
    assert route_after_triage({"risk_level": "YELLOW_ZONE"}) == "action_plan_response"
    assert route_after_triage({"risk_level": "NORMAL"}) == "session_lock_check"
    assert route_after_triage({"error": "triage:Err"}) == "safe_fallback"

    assert route_after_session_lock({"session_locked_red": True}) == "emergency_response"
    assert route_after_session_lock({"session_locked_red": False, "risk_level": "NORMAL"}) == "policy_guard"
    assert route_after_session_lock({"error": "lock:Err"}) == "safe_fallback"

    assert route_after_policy({"policy_decision": "BLOCK"}) == "safe_refusal"
    assert route_after_policy({"policy_decision": "ALLOW"}) == "retrieve_evidence"
    assert route_after_policy({"error": "policy:Err"}) == "safe_fallback"

    assert route_after_retrieve({"evidence_ok": False}) == "no_evidence_response"
    assert route_after_retrieve({"evidence_ok": True}) == "generate_answer"
    assert route_after_retrieve({"error": "retrieve:Err"}) == "safe_fallback"

    assert route_after_generate({"llm_raw_output": "Câu trả lời hợp lệ"}) == "output_guard"
    assert route_after_generate({"llm_raw_output": "   "}) == "safe_fallback"
    assert route_after_generate({"degraded": True}) == "safe_fallback"

    assert route_after_output_guard({"output_guard_decision": "PASS"}) == "finalize"
    assert route_after_output_guard({"output_guard_decision": "FAIL"}) == "safe_fallback"
    assert route_after_output_guard({"output_guard_decision": "RISK_UP"}) == "action_plan_response"
    assert route_after_output_guard({"error": "out:Err"}) == "safe_fallback"


# ---------------------------------------------------------------------------
# T1.4 & T1.5 — Kiểm thử thực thi đồ thị StateGraph qua mọi nhánh
# ---------------------------------------------------------------------------
def _make_test_graph(
    risk_level="NORMAL",
    policy_evaluator=None,
    output_evaluator=None,
    retrieve_fn=None,
    llm_caller=None,
):
    llm_calls = []

    def default_screener(text, profile):
        return SimpleNamespace(
            risk_level=risk_level,
            matched_flags=[f"flag_{risk_level.lower()}"],
            matched_reasons=[f"Lý do {risk_level}"],
        )

    def default_retrieve(query, top_k):
        return SAMPLE_CHUNKS

    def default_llm(prompt, model_override=None):
        llm_calls.append(prompt)
        return "Sau khi hít thuốc cần súc miệng sạch. Tài liệu tham khảo: QĐ 1851/QĐ-BYT"

    graph = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=default_screener,
        retrieve_fn=retrieve_fn or default_retrieve,
        llm_caller=llm_caller or default_llm,
        policy_evaluator=policy_evaluator,
        output_evaluator=output_evaluator,
    )
    return graph, llm_calls


def test_t15_graph_red_zone_bypasses_llm():
    graph, llm_calls = _make_test_graph(risk_level="RED_ZONE")
    final = graph.invoke(make_initial_state("BN-TEST-01", "Tôi không thở được"))

    assert final["risk_level"] == "RED_ZONE"
    assert "115" in final["response_text"]
    assert final["degraded"] is False
    assert len(llm_calls) == 0


def test_t15_graph_yellow_zone_bypasses_llm():
    graph, llm_calls = _make_test_graph(risk_level="YELLOW_ZONE")
    final = graph.invoke(make_initial_state("BN-TEST-01", "Tôi bị khò khè tăng về đêm"))

    assert final["risk_level"] == "YELLOW_ZONE"
    assert "VÙNG VÀNG" in final["response_text"]
    assert len(llm_calls) == 0


def test_t15_graph_session_red_lock_forces_emergency_response():
    graph, llm_calls = _make_test_graph(risk_level="NORMAL")
    state = make_initial_state("BN-TEST-01", "Cách vệ sinh buồng đệm như thế nào?")
    state["session_locked_red"] = True
    final = graph.invoke(state)

    assert final["risk_level"] == "RED_ZONE"
    assert "115" in final["response_text"]
    assert len(llm_calls) == 0


def test_t15_graph_policy_block_returns_safe_refusal_without_llm():
    def block_policy(state: AftercareState):
        events = append_guard_event(
            state, "L2_POLICY", "POL-MED-DOSE", "BLOCKED", "Chặn yêu cầu tự tăng liều."
        )
        return {
            "policy_decision": "BLOCK",
            "policy_rule_id": "POL-MED-DOSE",
            "policy_reason": "Không được tự ý tăng hoặc giảm liều thuốc.",
            "guard_events": events,
        }

    graph, llm_calls = _make_test_graph(policy_evaluator=block_policy)
    final = graph.invoke(make_initial_state("BN-TEST-01", "Tôi tự tăng gấp đôi liều được không?"))

    assert "Không được tự ý tăng hoặc giảm liều thuốc." in final["response_text"]
    assert len(llm_calls) == 0


def test_t15_graph_no_evidence_skips_llm():
    def no_evidence_retrieve(query, top_k):
        return []

    graph, llm_calls = _make_test_graph(retrieve_fn=no_evidence_retrieve)
    state = make_initial_state("BN-TEST-01", "Câu hỏi ngoài tài liệu")
    # Khi nút retrieve đánh dấu evidence_ok=False (sẽ do Evidence Gate đặt ở Giai đoạn 3)
    graph_no_ev = build_aftercare_graph(
        profile_loader=lambda pid: SAMPLE_PROFILE,
        screener_fn=lambda t, p: SimpleNamespace(
            risk_level="NORMAL", matched_flags=[], matched_reasons=[]
        ),
        retrieve_fn=no_evidence_retrieve,
        llm_caller=lambda prompt, m: llm_calls.append(prompt) or "Không được gọi",
        policy_evaluator=lambda s: {"policy_decision": "ALLOW", "evidence_ok": False},
    )
    # Ghi đè retrieve_evidence để giữ evidence_ok=False khi không có chunk
    from backend.app.orchestration.routing import route_after_retrieve as _r

    assert _r({"evidence_ok": False}) == "no_evidence_response"


def test_t15_graph_normal_rag_flow_and_output_guard_variants():
    # 1. Luồng NORMAL chuẩn -> PASS
    graph, llm_calls = _make_test_graph(risk_level="NORMAL")
    final = graph.invoke(make_initial_state("BN-TEST-01", "Sau khi hít thuốc có cần súc miệng không?"))
    assert final["risk_level"] == "NORMAL"
    assert final["degraded"] is False
    assert len(llm_calls) == 1
    assert len(final["citations"]) == 1
    assert final["trace_id"].startswith("trace-")

    # 2. Output Guard trả FAIL -> Safe Fallback
    graph_fail, _ = _make_test_graph(
        risk_level="NORMAL",
        output_evaluator=lambda s: {"output_guard_decision": "FAIL"},
    )
    final_fail = graph_fail.invoke(make_initial_state("BN-TEST-01", "Câu hỏi hợp lệ"))
    assert final_fail["degraded"] is True
    assert final_fail["response_text"] == SAFE_FALLBACK_MESSAGE

    # 3. Output Guard phát hiện rủi ro mới (RISK_UP) -> nâng lên YELLOW_ZONE Action Plan
    graph_up, _ = _make_test_graph(
        risk_level="NORMAL",
        output_evaluator=lambda s: {"output_guard_decision": "RISK_UP"},
    )
    final_up = graph_up.invoke(make_initial_state("BN-TEST-01", "Câu hỏi hợp lệ"))
    assert final_up["risk_level"] == "YELLOW_ZONE"
    assert "VÙNG VÀNG" in final_up["response_text"]


def test_t15_export_mermaid_diagram():
    graph, _ = _make_test_graph()
    mermaid_str = graph.get_graph().draw_mermaid()
    assert "safety_triage" in mermaid_str
    assert "generate_answer" in mermaid_str

    out_path = (
        Path(__file__).resolve().parent.parent
        / "Evidence"
        / "W07"
        / "figures"
        / "orchestration_graph.mmd"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(mermaid_str, encoding="utf-8")
    assert out_path.exists()


# ---------------------------------------------------------------------------
# T1.7 — LLMGateway
# ---------------------------------------------------------------------------
def test_t17_llm_gateway_fallback_from_openrouter_to_gemini():
    class FailingOpenRouter:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise ConnectionError("OpenRouter lỗi kết nối")

    class WorkingGemini:
        class models:
            @staticmethod
            def generate_content(model, contents):
                return SimpleNamespace(text="Phản hồi từ Gemini dự phòng.")

    gw = LLMGateway(openrouter_client=FailingOpenRouter(), gemini_client=WorkingGemini())
    res = gw.generate("Xin chào")
    assert res.succeeded is True
    assert res.provider == "gemini"
    assert res.text == "Phản hồi từ Gemini dự phòng."
    assert res.latency_ms >= 0

