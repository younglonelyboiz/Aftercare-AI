"""
KIỂM THỬ GIAI ĐOẠN 0 — VÁ LỖ HỔNG AN TOÀN (W07-PHASE0)

T0.1  Chat Vùng Đỏ/Vàng phải tạo AlertTicket (Zero-Silent Failure)
T0.2  LLM/hệ thống lỗi -> thông điệp an toàn, không lộ lỗi kỹ thuật (Fail-safe)
T0.3  Pipeline chat không chặn event loop (WebSocket điều dưỡng không bị trễ)
T0.4  model_override ngoài whitelist bị bỏ qua

Bộ test KHÔNG cần PostgreSQL, GPU hay API key: retriever, LLM và
EscalationService đều được thay bằng bản giả lập.
"""
import asyncio
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.app.rag.service as rag_service_module


# ---------------------------------------------------------------------------
# Giả lập các phụ thuộc nặng (DB / model / LLM)
# ---------------------------------------------------------------------------
class FakeRetriever:
    def retrieve(self, query, top_k=3):
        return [
            {
                "chunk_id": "c1",
                "section_title": "Súc miệng sau khi hít ICS",
                "citation": "QĐ 1851/QĐ-BYT, Mục 2.7.2",
                "safety_tier": "KHO_2",
                "document_tag": "byt_1851",
                "document_name": "Hướng dẫn HPQ - BYT",
                "pdf_page": 12,
                "content": "Súc miệng bằng nước sạch sau khi hít corticoid.",
                "similarity_score": 0.91,
            }
        ]


rag_service_module.PgVectorRetriever = FakeRetriever  # phải đặt trước khi import chat

from backend.app.api.v1.endpoints import chat as chat_module  # noqa: E402
from backend.app.rag.safe_messages import SAFE_FALLBACK_MESSAGE  # noqa: E402
from backend.app.core.config import settings  # noqa: E402

RED_MSG = "Tôi không thở được, tím môi, xịt ventolin 2 lần rồi mà vẫn không đỡ"
YELLOW_MSG = "Đêm qua tôi bị thức giấc ban đêm vì ho, khò khè tăng và tức ngực"
NORMAL_MSG = "Sau khi hít Symbicort tôi có cần súc miệng không?"
PATIENT_ID = "BN-2026-ASTHMA-02"  # hồ sơ thật trong Data/patient_profiles


class FakeEscalationService:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def create_or_escalate_ticket(self, **kwargs):
        if self.fail:
            raise RuntimeError("DB connection refused")
        self.calls.append(kwargs)
        return SimpleNamespace(id=f"ticket-test-{len(self.calls)}")


def make_client(escalation_service):
    app = FastAPI()
    app.include_router(chat_module.router, prefix="/api/v1/chat")
    app.dependency_overrides[chat_module.get_escalation_service] = lambda: escalation_service
    return TestClient(app)


@pytest.fixture
def llm_calls(monkeypatch):
    """Đếm số lần gọi LLM, mặc định trả lời thành công."""
    calls = []

    def fake_llm(prompt, model_override=None):
        calls.append(prompt)
        return "Có, cần súc miệng sau khi hít. Tài liệu tham khảo: QĐ 1851/QĐ-BYT"

    monkeypatch.setattr(chat_module.rag_service, "_call_llm", fake_llm)
    return calls


# ---------------------------------------------------------------------------
# T0.1 — Chat Đỏ/Vàng tạo AlertTicket
# ---------------------------------------------------------------------------
def test_t01_red_chat_creates_p0_ticket_and_never_calls_llm(llm_calls):
    esc = FakeEscalationService()
    res = make_client(esc).post("/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": RED_MSG})

    assert res.status_code == 200
    body = res.json()
    assert body["safety_status"] == "RED_ZONE"
    assert body["escalation_ticket_id"] == "ticket-test-1"
    assert "115" in body["response"]
    assert len(llm_calls) == 0, "Vùng Đỏ tuyệt đối không được gọi LLM"

    assert len(esc.calls) == 1
    call = esc.calls[0]
    assert call["priority"] == "P0_CRITICAL"
    assert call["alert_type"] == "CHAT_RED_FLAG_DETECTION"
    assert call["patient_id"] == PATIENT_ID
    assert call["clinical_data"]["source"] == "CHAT"
    assert call["clinical_data"]["matched_flags"], "Phải mang theo cờ lâm sàng cho điều dưỡng"
    assert "screener" not in body, "Trường nội bộ không được lộ ra API"


def test_t01_yellow_chat_creates_p1_ticket(llm_calls):
    esc = FakeEscalationService()
    res = make_client(esc).post("/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": YELLOW_MSG})

    body = res.json()
    assert body["safety_status"] == "YELLOW_ZONE"
    assert esc.calls[0]["priority"] == "P1_HIGH"
    assert esc.calls[0]["alert_type"] == "CHAT_YELLOW_ZONE_ALERT"
    assert len(llm_calls) == 0


def test_t01_normal_chat_creates_no_ticket(llm_calls):
    esc = FakeEscalationService()
    res = make_client(esc).post("/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": NORMAL_MSG})

    body = res.json()
    assert body["safety_status"] == "NORMAL"
    assert body["escalation_ticket_id"] is None
    assert esc.calls == []
    assert len(llm_calls) == 1
    assert body["citations"], "Câu trả lời RAG phải kèm trích dẫn"


def test_t01_ticket_failure_does_not_block_emergency_response(llm_calls):
    esc = FakeEscalationService(fail=True)
    res = make_client(esc).post("/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": RED_MSG})

    assert res.status_code == 200
    body = res.json()
    assert body["safety_status"] == "RED_ZONE"
    assert "115" in body["response"]
    assert body["escalation_ticket_id"] is None


def test_t01_profile_without_action_plan_does_not_crash(llm_calls, monkeypatch):
    profile = {
        "patient_info": {"patient_id": "BN-NO-PLAN", "full_name": "Bệnh nhân thử"},
        "clinical_status": {"personal_best_pef": 400},
        "current_medications": {},
        "follow_up": {},
    }
    monkeypatch.setattr(chat_module.rag_service, "get_patient_profile", lambda pid: profile)
    res = make_client(FakeEscalationService()).post(
        "/api/v1/chat/chat", json={"patient_id": "BN-NO-PLAN", "message": RED_MSG}
    )
    assert res.status_code == 200
    assert res.json()["safety_status"] == "RED_ZONE"


# ---------------------------------------------------------------------------
# T0.2 — Fail-safe khi LLM / hệ thống lỗi
# ---------------------------------------------------------------------------
def test_t02_all_llm_providers_fail_returns_safe_fallback(monkeypatch):
    svc = chat_module.rag_service

    class Boom:
        def __getattr__(self, name):
            raise ConnectionError("network unreachable sk-secret-key")

    monkeypatch.setattr(svc, "openrouter_client", SimpleNamespace(chat=Boom()))
    monkeypatch.setattr(svc, "gemini_client", SimpleNamespace(models=Boom()))

    res = make_client(FakeEscalationService()).post(
        "/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": NORMAL_MSG}
    )
    body = res.json()
    assert res.status_code == 200
    assert body["degraded"] is True
    assert body["response"] == SAFE_FALLBACK_MESSAGE
    assert "Lỗi" not in body["response"] and "sk-secret" not in body["response"]
    assert "115" in body["response"]


def test_t02_empty_llm_output_returns_safe_fallback(monkeypatch):
    monkeypatch.setattr(chat_module.rag_service, "_call_llm", lambda p, model_override=None: "   ")
    body = make_client(FakeEscalationService()).post(
        "/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": NORMAL_MSG}
    ).json()
    assert body["degraded"] is True
    assert body["response"] == SAFE_FALLBACK_MESSAGE


def test_t02_unexpected_exception_returns_safe_fallback_not_500(monkeypatch):
    def explode(**kwargs):
        raise RuntimeError("psycopg2.OperationalError: password authentication failed")

    monkeypatch.setattr(chat_module.rag_service, "process_chat", explode)
    res = make_client(FakeEscalationService()).post(
        "/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": NORMAL_MSG}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["degraded"] is True
    assert "psycopg2" not in body["response"] and "password" not in body["response"]


def test_t02_unknown_patient_still_404(llm_calls):
    res = make_client(FakeEscalationService()).post(
        "/api/v1/chat/chat", json={"patient_id": "KHONG-TON-TAI", "message": NORMAL_MSG}
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# T0.3 — Không chặn event loop
# ---------------------------------------------------------------------------
def test_t03_slow_llm_does_not_block_event_loop(monkeypatch):
    def slow_llm(prompt, model_override=None):
        time.sleep(1.5)  # giả lập LLM chậm (gọi đồng bộ)
        return "Trả lời chậm. Tài liệu tham khảo: BYT"

    monkeypatch.setattr(chat_module.rag_service, "_call_llm", slow_llm)

    app = FastAPI()
    app.include_router(chat_module.router, prefix="/api/v1/chat")
    app.dependency_overrides[chat_module.get_escalation_service] = lambda: FakeEscalationService()

    @app.get("/ping")
    async def ping():  # đại diện cho heartbeat WebSocket / API cảnh báo
        return {"ok": True}

    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            chat_task = asyncio.create_task(
                client.post("/api/v1/chat/chat", json={"patient_id": PATIENT_ID, "message": NORMAL_MSG})
            )
            await asyncio.sleep(0.2)  # để request chat bắt đầu xử lý
            t0 = time.perf_counter()
            ping = await client.get("/ping")
            ping_latency = time.perf_counter() - t0
            chat_res = await chat_task
            return ping, ping_latency, chat_res

    ping, ping_latency, chat_res = asyncio.run(scenario())
    assert ping.status_code == 200
    assert ping_latency < 0.5, f"Event loop bị chặn: ping mất {ping_latency:.2f}s"
    assert chat_res.status_code == 200


# ---------------------------------------------------------------------------
# T0.4 — Whitelist model
# ---------------------------------------------------------------------------
def test_t04_model_override_outside_whitelist_is_ignored():
    svc = chat_module.rag_service
    assert svc._resolve_model("attacker/expensive-model") is None
    assert svc._resolve_model(settings.OPENROUTER_MODEL) == settings.OPENROUTER_MODEL
    assert svc._resolve_model(None) is None


def test_t04_chat_request_does_not_expose_model_override():
    from backend.app.schemas.chat import ChatRequest

    assert "model_override" not in ChatRequest.model_fields

