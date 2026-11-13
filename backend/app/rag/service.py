"""
Service mặt tiền (Facade) điều phối luồng hội thoại Aftercare-AI qua LangGraph StateGraph — [W07-T1.6].
"""
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.core.config import settings
from backend.app.guardrails.templates_vi import (
    DEFAULT_RED_ACTION,
    DEFAULT_YELLOW_ACTION,
)
from backend.app.llm.gateway import LLMGateway
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.state import AftercareState, make_initial_state
from backend.app.rag.retriever import PgVectorRetriever

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger("AftercareRAGService")


class AftercareRAGService:
    """Service mặt tiền điều phối toàn bộ luồng Triage, Guardrails và RAG qua LangGraph."""

    def __init__(
        self,
        policy_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
        output_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
    ):
        self.retriever = PgVectorRetriever()
        self.triage = TriageAgent()
        self.llm_gateway = LLMGateway()

        # Giữ thuộc tính tương thích ngược với các bài kiểm thử hiện có
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openrouter_client = self.llm_gateway.openrouter_client
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_client = self.llm_gateway.gemini_client

        # Xây dựng đồ thị điều phối LangGraph StateGraph.
        # Các nút gọi qua lambda tới phương thức của instance để hỗ trợ dependency override / monkeypatch.
        self.graph = build_aftercare_graph(
            profile_loader=lambda pid: self.get_patient_profile(pid),
            screener_fn=lambda text, prof: self.triage.evaluate_full_text(text, prof),
            retrieve_fn=lambda q, top_k: self.retriever.retrieve(query=q, top_k=top_k),
            llm_caller=lambda prompt, model_override: self._call_llm(
                prompt, model_override=model_override
            ),
            policy_evaluator=policy_evaluator,
            output_evaluator=output_evaluator,
            top_k=3,
        )

    def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        profiles_dir = BASE_DIR / "Data" / "patient_profiles"
        for p_file in profiles_dir.glob("*.json"):
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("patient_info", {}).get("patient_id") == patient_id:
                    return data
        raise ValueError(f"Không tìm thấy hồ sơ cho bệnh nhân có mã: {patient_id}")

    def process_chat(
        self,
        patient_id: str,
        message: str,
        model_override: Optional[str] = None,
        session_id: Optional[str] = None,
        session_locked_red: bool = False,
    ) -> Dict[str, Any]:
        """Thực thi một lượt hội thoại thông qua đồ thị LangGraph StateGraph."""
        initial_state = make_initial_state(
            patient_id=patient_id,
            message=message,
            session_id=session_id,
            model_override=model_override,
            channel="CHAT",
        )
        initial_state["session_locked_red"] = session_locked_red

        final_state: AftercareState = self.graph.invoke(initial_state)

        return {
            "response": final_state.get("response_text", ""),
            "safety_status": final_state.get("risk_level", "NORMAL"),
            "citations": final_state.get("citations") or [],
            "degraded": bool(final_state.get("degraded", False)),
            "trace_id": final_state.get("trace_id"),
            "guard_events": list(final_state.get("guard_events") or []),
            "latency_ms": dict(final_state.get("latency_ms") or {}),
            "screener": final_state.get("screener_result")
            or {"matched_flags": [], "matched_reasons": []},
        }

    def _resolve_model(self, model_override: Optional[str]) -> Optional[str]:
        """Ủy quyền kiểm tra danh sách trắng mô hình cho LLMGateway."""
        return self.llm_gateway.resolve_model(model_override)

    def _call_llm(
        self, prompt: str, model_override: Optional[str] = None
    ) -> Optional[str]:
        """Gọi LLM thông qua LLMGateway (đồng bộ hóa client nếu có monkeypatch)."""
        self.llm_gateway.openrouter_client = self.openrouter_client
        self.llm_gateway.gemini_client = self.gemini_client
        result = self.llm_gateway.generate(prompt, model_override=model_override)
        return result.text


__all__ = [
    "AftercareRAGService",
    "DEFAULT_RED_ACTION",
    "DEFAULT_YELLOW_ACTION",
]
