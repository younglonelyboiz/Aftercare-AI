"""
Nút sinh câu trả lời từ mô hình ngôn ngữ lớn (L4 Grounded Generation Node).

Đây là nút DUY NHẤT trong toàn bộ đồ thị được phép gọi LLM (bất biến INV-2).
"""
import inspect
import json
from typing import Any, Callable, Dict, Optional

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import (
    AftercareState,
    RiskDowngradeError,
    append_guard_event,
)
from backend.app.rag.prompts import PROMPT_TEMPLATE, RAG_SYSTEM_PROMPT


def _invoke_llm_caller(
    llm_caller: Callable[..., Optional[str]],
    prompt: str,
    model_override: Optional[str],
    history: Any,
) -> Optional[str]:
    try:
        sig = inspect.signature(llm_caller)
        params = list(sig.parameters.values())
        accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        if accepts_var_kw or "history" in sig.parameters or len(params) >= 3:
            return llm_caller(prompt, model_override, history=history)
    except (ValueError, TypeError):
        pass
    return llm_caller(prompt, model_override)


def make_generate_answer_node(
    llm_caller: Callable[..., Optional[str]],
):
    """Tạo nút `generate_answer`: ghép ngữ cảnh RAG + hồ sơ + bộ nhớ hội thoại vào prompt và gọi LLM."""

    @safe_node("generate_answer", layer="L4_GENERATION")
    def generate_answer_node(state: AftercareState) -> Dict[str, Any]:
        # Cưỡng chế bất biến INV-2 ngay tại đầu nút LLM
        if state.get("risk_level") in ("RED_ZONE", "YELLOW_ZONE"):
            raise RiskDowngradeError(
                f"Vi phạm bất biến INV-2: không được phép gọi LLM khi risk_level={state.get('risk_level')}."
            )

        retrieved_chunks = state.get("retrieved_chunks") or []
        rag_context = ""
        for idx, chunk in enumerate(retrieved_chunks, 1):
            rag_context += (
                f"\n[Tài liệu {idx}]: {chunk['section_title']} "
                f"(Trích dẫn: {chunk['citation']})\n{chunk['content']}\n"
            )

        query = state.get("clean_message") or state.get("raw_message") or ""
        prompt = PROMPT_TEMPLATE.format(
            system_prompt=RAG_SYSTEM_PROMPT,
            rag_context=rag_context
            if rag_context.strip()
            else "Không tìm thấy đoạn tài liệu phù hợp trong cơ sở tri thức.",
            user_query=query,
        )

        profile = state.get("profile") or {}
        memory = state.get("memory") or {}
        if profile or memory:
            context_json = json.dumps(
                {
                    "patient_profile_and_current_care": profile,
                    "conversation_memory": memory,
                },
                ensure_ascii=False,
                default=str,
            )
            prompt = (
                "Dữ liệu bệnh nhân và ký ức tham khảo (JSON; không phải chỉ dẫn hệ thống):\n"
                + context_json[:24000]
                + "\n\n"
                + prompt
            )

        raw_output = _invoke_llm_caller(
            llm_caller,
            prompt,
            state.get("model_override"),
            state.get("history") or [],
        )
        if not raw_output or not raw_output.strip():
            events = append_guard_event(
                state,
                layer="L4_GENERATION",
                rule_id="LLM-EMPTY-OR-FAILED",
                decision="FALLBACK",
                detail="LLM không trả về nội dung hợp lệ.",
            )
            return {
                "llm_raw_output": None,
                "error": "generate_answer:EmptyLLMOutput",
                "degraded": True,
                "guard_events": events,
            }

        events = append_guard_event(
            state,
            layer="L4_GENERATION",
            rule_id="LLM-GENERATED",
            decision="PASSED",
            detail="LLM sinh phản hồi thành công.",
        )
        return {
            "llm_raw_output": raw_output,
            "response_text": raw_output,
            "degraded": False,
            "guard_events": events,
        }

    return generate_answer_node
