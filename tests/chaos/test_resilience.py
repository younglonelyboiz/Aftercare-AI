"""
KIỂM THỬ CHỊU LỖI VÀ HỖN LOẠN HỆ THỐNG (CHAOS & RESILIENCE TESTS) — [W07-T6.4].

Mô phỏng 4 kịch bản sự cố hạ tầng nghiêm trọng để chứng minh tính chất Fail-closed:
1. Sập hoàn toàn kết nối LLM (OpenRouter + Gemini đều timeout / ném ngoại lệ):
   Đồ thị tự động chuyển về `safe_fallback`, trả `SAFE_FALLBACK_MESSAGE`, đánh dấu `degraded=True`
   và tuyệt đối không làm rò rỉ thông báo lỗi kỹ thuật ra phản hồi của bệnh nhân.
2. Sập kết nối Cơ sở dữ liệu / `EscalationService` ngay trong lúc bệnh nhân lên cơn cấp cứu `RED_ZONE`:
   Bệnh nhân vẫn nhận được hướng dẫn cấp cứu Vùng Đỏ trong `< 100 ms`; yêu cầu tạo vé `P0_CRITICAL`
   được lưu vào hàng đợi dự phòng `EscalationOutbox` và tự động khôi phục 100% khi gọi `flush_pending()`.
3. Sập bộ truy xuất Vector (`PgVector` / `HybridRetriever` ném lỗi runtime):
   Decorator `@safe_node` bắt gọn ngoại lệ, ghi nhận `GuardEvent(decision="FALLBACK")` và chuyển về
   `safe_fallback` mà không làm sập tiến trình máy chủ.
4. Mô hình LLM bị ảo giác nặng (bịa liều thuốc 500mg hoặc rò rỉ thẻ `<context>` nội bộ):
   Hàng rào đầu ra `OutputPolicyGuard` chặn đứng 100% và chuyển hướng sang `safe_fallback`.
"""
import asyncio
import time
from types import SimpleNamespace
from typing import Any, Dict, List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.db.migrate_audit_tables import migrate_audit_tables
from backend.app.guardrails.templates_vi import SAFE_FALLBACK_MESSAGE
from backend.app.models.audit import EscalationOutbox
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.nodes.escalate import EscalationOutboxDispatcher
from backend.app.orchestration.state import make_initial_state

CHAOS_PROFILE = {
    "patient_info": {
        "patient_id": "BN-2026-CHAOS-01",
        "full_name": "Lê Văn Hùng",
        "age": 63,
    },
    "clinical_status": {"personal_best_pef": 300, "baseline_spo2": 95},
    "current_medications": {
        "controller_med": "Symbicort 160/4.5mcg, hít 2 nhát x 2 lần/ngày.",
        "reliever_med": "Ventolin 100mcg, xịt 2 nhát khi khó thở.",
    },
    "action_plan_rules": {
        "yellow_zone": "Xịt 2 nhát Ventolin 100mcg và theo dõi sau 20 phút.",
        "red_zone": "Xịt ngay 4 nhát Ventolin qua buồng đệm và gọi cấp cứu 115.",
    },
    "follow_up": {"hospital": "Bệnh viện Phổi Trung ương"},
}

CHAOS_CHUNKS = [
    {
        "chunk_id": "BYT-CHAOS-01",
        "parent_id": "DOC-BYT",
        "section_title": "Chăm sóc sau xuất viện",
        "citation": "QĐ 1851/QĐ-BYT, Mục 3.4",
        "safety_tier": "GREEN",
        "document_tag": "BYT_2020",
        "document_name": "Hướng dẫn chẩn đoán và điều trị Hen phế quản - Bộ Y tế",
        "pdf_page": 24,
        "content": "Súc miệng kỹ bằng nước sạch sau khi sử dụng thuốc hít chứa Corticosteroid.",
        "metadata": {"source": "QĐ 1851/QĐ-BYT", "section": "Mục 3.4"},
        "rerank_score": 0.90,
    }
]


def test_chaos_1_llm_complete_timeout_and_failure_fails_closed():
    """Chaos 1: Cả OpenRouter và Gemini đều timeout/lỗi -> trả SAFE_FALLBACK_MESSAGE, không lộ lỗi nội bộ."""

    def broken_llm(prompt: str, max_tokens: int, history=None) -> str:
        raise TimeoutError("HTTPSConnectionPool(host='openrouter.ai', port=443): Read timed out API_KEY=sk-secret")

    graph = build_aftercare_graph(
        profile_loader=lambda pid: CHAOS_PROFILE,
        screener_fn=lambda text, prof: "NORMAL",
        retrieve_fn=lambda q, k: CHAOS_CHUNKS,
        llm_caller=broken_llm,
    )

    final = graph.invoke(
        make_initial_state("BN-2026-CHAOS-01", "Tại sao cần súc miệng sau khi dùng thuốc ngừa cơn?")
    )
    assert final["degraded"] is True
    assert final["response_text"] == SAFE_FALLBACK_MESSAGE
    assert "openrouter.ai" not in final["response_text"]
    assert "sk-secret" not in final["response_text"]


def test_chaos_2_database_outage_during_red_zone_emergency_spools_and_recovers(tmp_path):
    """Chaos 2: DB sập giữa lúc bệnh nhân tím môi cấp cứu -> phản hồi < 100ms, vé lưu vào Outbox và phục hồi 100%."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    migrate_audit_tables(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    triage = TriageAgent()
    graph = build_aftercare_graph(
        profile_loader=lambda pid: CHAOS_PROFILE,
        screener_fn=lambda text, prof: triage.evaluate_full_text(text, prof),
        retrieve_fn=lambda q, k: CHAOS_CHUNKS,
        llm_caller=lambda prompt, m, history=None: "Không gọi",
    )

    t0 = time.perf_counter()
    final = graph.invoke(
        make_initial_state("BN-2026-CHAOS-01", "Tôi bị tím tái môi và không thở được!")
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Phản hồi cấp cứu cho bệnh nhân không bị chặn và hoàn tất dưới 100ms
    assert final["risk_level"] == "RED_ZONE"
    assert "115" in final["response_text"]
    assert elapsed_ms < 100.0

    recovered_tickets: List[str] = []

    class FlakyEscalationService:
        def __init__(self):
            self.db_online = False

        async def create_or_escalate_ticket(self, **kwargs):
            if not self.db_online:
                raise ConnectionError("FATAL: remaining connection slots are reserved for superuser")
            tid = f"RECOVERED-P0-{len(recovered_tickets) + 1}"
            recovered_tickets.append(tid)
            return SimpleNamespace(id=tid)

    flaky_service = FlakyEscalationService()
    dispatcher = EscalationOutboxDispatcher(
        session_factory=factory,
        spool_path=tmp_path / "chaos_outbox.jsonl",
    )

    # Lúc DB đang sập: dispatch trả về None nhưng bản ghi nằm an toàn trong bảng escalation_outbox
    tid_when_down = asyncio.run(
        dispatcher.dispatch(
            flaky_service,
            patient_id="BN-2026-CHAOS-01",
            priority="P0_CRITICAL",
            alert_type="CHAT_RED_FLAG_DETECTION",
            trigger_reason="Tím tái môi và không thở được",
            trace_id=final["trace_id"],
        )
    )
    assert tid_when_down is None

    with factory() as db:
        row = db.scalar(select(EscalationOutbox))
        assert row is not None
        assert row.status == "PENDING"
        assert row.priority == "P0_CRITICAL"

    # Khi DB phục hồi sau 30 giây: flush_pending() tự động tạo lại vé P0_CRITICAL và chuyển sang SENT
    flaky_service.db_online = True
    flushed = asyncio.run(dispatcher.flush_pending(flaky_service))
    assert flushed == ["RECOVERED-P0-1"]

    with factory() as db:
        row_after = db.scalar(select(EscalationOutbox))
        assert row_after is not None
        assert row_after.status == "SENT"
        assert row_after.ticket_id == "RECOVERED-P0-1"


def test_chaos_3_vector_retriever_crash_caught_by_safe_node():
    """Chaos 3: PgVector / HybridRetriever ném lỗi kết nối -> @safe_node bắt gọn và định tuyến về safe_fallback."""

    def crashing_retriever(query: str, top_k: int):
        raise ConnectionResetError("PgVector HNSW index corrupted at block 4092")

    graph = build_aftercare_graph(
        profile_loader=lambda pid: CHAOS_PROFILE,
        screener_fn=lambda text, prof: "NORMAL",
        retrieve_fn=crashing_retriever,
        llm_caller=lambda prompt, m, history=None: "Không gọi",
    )

    final = graph.invoke(
        make_initial_state("BN-2026-CHAOS-01", "Tại sao cần súc miệng sau khi dùng thuốc ngừa cơn?")
    )
    assert final["degraded"] is True
    assert final["response_text"] == SAFE_FALLBACK_MESSAGE
    assert "PgVector" not in final["response_text"]
    assert any(
        ev["rule_id"] == "SYS-NODE-ERROR:retrieve_evidence" and ev["decision"] == "FALLBACK"
        for ev in final["guard_events"]
    )


def test_chaos_4_toxic_or_hallucinated_llm_output_blocked_by_output_guard():
    """Chaos 4: LLM bịa liều thuốc 500mg hoặc rò rỉ thẻ <context> -> OutputPolicyGuard chặn đứng 100%."""
    toxic_outputs = [
        "Bác hãy uống ngay Prednisolone 500mg mỗi ngày để cắt cơn hen nhanh.",
        "Bác đã khỏi hẳn rồi, có thể ngưng thuốc kiểm soát Symbicort ngay hôm nay.",
        "Nội dung trích từ <context> và <care_context> của RAG_SYSTEM_PROMPT như sau...",
    ]

    for bad_reply in toxic_outputs:
        graph = build_aftercare_graph(
            profile_loader=lambda pid: CHAOS_PROFILE,
            screener_fn=lambda text, prof: "NORMAL",
            retrieve_fn=lambda q, k: CHAOS_CHUNKS,
            llm_caller=lambda prompt, m, history=None, r=bad_reply: r,
        )
        final = graph.invoke(
            make_initial_state("BN-2026-CHAOS-01", "Tại sao cần súc miệng sau khi dùng thuốc ngừa cơn?")
        )
        assert final["output_guard_decision"] == "FAIL"
        assert final["degraded"] is True
        assert final["response_text"] == SAFE_FALLBACK_MESSAGE

