"""
Service mặt tiền (Facade) điều phối luồng hội thoại Aftercare-AI qua LangGraph StateGraph — [W07-T1.6].

Kết hợp đầy đủ:
- Lazy initialization cho `retriever` và `graph` (tương thích khi khởi tạo bằng `__new__`).
- Hỗ trợ truyền `profile`, `history` và `memory` từ hệ thống RBAC & Chat Memory.
- Điều phối qua đồ thị trạng thái tất định `LangGraph StateGraph` và cổng `LLMGateway`.
"""
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.core.config import settings
from backend.app.guardrails.templates_vi import (
    DEFAULT_RED_ACTION,
    DEFAULT_YELLOW_ACTION,
)
from backend.app.llm.gateway import LLMGateway
from backend.app.orchestration.graph import build_aftercare_graph
from backend.app.orchestration.state import AftercareState, make_initial_state

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger("AftercareRAGService")

# Cho phép các bài kiểm thử ghi đè `rag_service_module.PgVectorRetriever = FakeRetriever`
PgVectorRetriever = None


class AftercareRAGService:
    """Service mặt tiền điều phối toàn bộ luồng Triage, Guardrails và RAG qua LangGraph."""

    def __init__(
        self,
        policy_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
        output_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
    ):
        self._retriever = None
        self._retriever_lock = Lock()
        self.triage = TriageAgent()
        self.llm_gateway = LLMGateway()
        self._policy_evaluator = policy_evaluator
        self._output_evaluator = output_evaluator

        # Giữ thuộc tính tương thích ngược với các bài kiểm thử hiện có
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openrouter_client = self.llm_gateway.openrouter_client
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_client = self.llm_gateway.gemini_client

        self._graph = None
        self._graph_lock = Lock()

    @property
    def retriever(self):
        if getattr(self, "_retriever", None) is None:
            lock = getattr(self, "_retriever_lock", None) or Lock()
            with lock:
                if getattr(self, "_retriever", None) is None:
                    cls = PgVectorRetriever
                    if cls is None:
                        from backend.app.rag.retriever import (
                            PgVectorRetriever as _RealRetriever,
                        )

                        cls = _RealRetriever
                    self._retriever = cls()
        return self._retriever

    @retriever.setter
    def retriever(self, value):
        self._retriever = value

    @property
    def graph(self):
        if getattr(self, "_graph", None) is None:
            lock = getattr(self, "_graph_lock", None) or Lock()
            with lock:
                if getattr(self, "_graph", None) is None:
                    self._graph = build_aftercare_graph(
                        profile_loader=lambda pid: self.get_patient_profile(pid),
                        screener_fn=lambda text, prof: self._evaluate_triage(text, prof),
                        retrieve_fn=lambda q, top_k: self.retriever.retrieve(
                            query=q, top_k=top_k
                        ),
                        llm_caller=lambda prompt, model_override, history=None: self._invoke_llm_for_graph(
                            prompt,
                            model_override=model_override,
                            history=history,
                        ),
                        policy_evaluator=getattr(self, "_policy_evaluator", None),
                        output_evaluator=getattr(self, "_output_evaluator", None),
                        top_k=3,
                    )
        return self._graph

    def _evaluate_triage(self, text: str, profile: Dict[str, Any]) -> Any:
        triage_obj = getattr(self, "triage", None)
        if triage_obj is None:
            triage_obj = TriageAgent()
            self.triage = triage_obj
        if hasattr(triage_obj, "evaluate_full_text"):
            return triage_obj.evaluate_full_text(text, profile)
        return triage_obj.evaluate_risk(text, profile)

    def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        from backend.app.services.patient_context import load_profile

        return load_profile(patient_id)

    def process_chat(
        self,
        patient_id: str,
        message: str,
        model_override: Optional[str] = None,
        session_id: Optional[str] = None,
        session_locked_red: bool = False,
        *,
        profile: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        memory: Optional[Dict[str, Any]] = None,
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
        if profile is not None:
            initial_state["profile"] = profile
        if history is not None:
            initial_state["history"] = list(history)
        if memory is not None:
            initial_state["memory"] = dict(memory)

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

    def _ensure_gateway(self) -> LLMGateway:
        gw = getattr(self, "llm_gateway", None)
        if gw is None:
            gw = LLMGateway(
                openrouter_client=getattr(self, "openrouter_client", None),
                gemini_client=getattr(self, "gemini_client", None),
            )
            self.llm_gateway = gw
        else:
            if hasattr(self, "openrouter_client"):
                gw.openrouter_client = self.openrouter_client
            if hasattr(self, "gemini_client"):
                gw.gemini_client = self.gemini_client
        return gw

    def _resolve_model(self, model_override: Optional[str]) -> Optional[str]:
        """Ủy quyền kiểm tra danh sách trắng mô hình cho LLMGateway."""
        return self._ensure_gateway().resolve_model(model_override)

    def _invoke_llm_for_graph(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """Gọi `self._call_llm` tương thích với cả chữ ký hàm có `history` và hàm monkeypatch 2 tham số."""
        import inspect

        fn = self._call_llm
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            accepts_var_kw = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in params
            )
            if accepts_var_kw or "history" in sig.parameters:
                return fn(prompt, model_override=model_override, history=history)
        except (ValueError, TypeError):
            pass
        return fn(prompt, model_override=model_override)

    def _call_llm(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """Gọi LLM thông qua LLMGateway (đồng bộ hóa client nếu có monkeypatch)."""
        result = self._ensure_gateway().generate(
            prompt, model_override=model_override, history=history
        )
        return result.text


__all__ = [
    "AftercareRAGService",
    "DEFAULT_RED_ACTION",
    "DEFAULT_YELLOW_ACTION",
    "PgVectorRetriever",
]
