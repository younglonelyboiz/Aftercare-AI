"""
Nút sinh câu trả lời từ mô hình ngôn ngữ lớn (L4 Grounded Generation Node) — [W07-T3.3, T3.4, T3.5].

Đây là nút DUY NHẤT trong toàn bộ đồ thị được phép gọi LLM (bất biến INV-2).
Trước khi gửi dữ liệu tới LLM, nút này thực hiện:
1. Kiểm tra cưỡng chế `INV-2` (không gọi LLM ở Vùng Đỏ/Vàng) và `INV-5` (`evidence_ok == True`).
2. Ẩn danh toàn bộ thông tin định danh cá nhân (PII Redactor — `INV-6`) trên hồ sơ, lịch sử
   5 lượt hội thoại gần nhất, ghi nhớ dài hạn và câu hỏi hiện tại.
3. Đóng gói dữ liệu không tin cậy vào các thẻ ranh giới XML (`<context>`, `<care_context>`,
   `<patient_message>`) và làm sạch các mệnh lệnh Indirect Prompt Injection.
"""
import inspect
import json
from typing import Any, Callable, Dict, Optional

from backend.app.guardrails.pii_redactor import PIIRedactor, default_pii_redactor
from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import (
    AftercareState,
    RiskDowngradeError,
    append_guard_event,
)
from backend.app.rag.prompts import RAG_SYSTEM_PROMPT, build_grounded_prompt


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
    pii_redactor: Optional[PIIRedactor] = None,
):
    """Tạo nút `generate_answer`: ẩn danh PII, đóng gói XML cô lập dữ liệu và gọi LLM."""
    redactor = pii_redactor or default_pii_redactor

    @safe_node("generate_answer", layer="L4_GENERATION")
    def generate_answer_node(state: AftercareState) -> Dict[str, Any]:
        # 1. Cưỡng chế bất biến INV-2 ngay tại đầu nút LLM
        if state.get("risk_level") in ("RED_ZONE", "YELLOW_ZONE"):
            raise RiskDowngradeError(
                f"Vi phạm bất biến INV-2: không được phép gọi LLM khi risk_level={state.get('risk_level')}."
            )
        # 2. Cưỡng chế bất biến INV-5 (Evidence Gate)
        if state.get("evidence_ok") is False:
            raise RuntimeError(
                "Vi phạm bất biến INV-5: không được phép gọi LLM khi evidence_ok=False."
            )

        raw_profile = state.get("profile") or {}
        raw_memory = state.get("memory") or {}
        raw_history = state.get("history") or []
        raw_query = state.get("clean_message") or state.get("raw_message") or ""

        # 3. Ẩn danh thông tin định danh cá nhân (INV-6: No PII Egress)
        safe_profile = redactor.redact_profile(raw_profile)
        safe_memory = redactor.redact_memory(raw_memory, profile=raw_profile)
        safe_history = redactor.redact_history(
            raw_history, profile=raw_profile, max_turns=5
        )
        safe_query = redactor.redact_text(raw_query, profile=raw_profile)

        retrieved_chunks = state.get("retrieved_chunks") or []
        rag_context = ""
        for idx, chunk in enumerate(retrieved_chunks, 1):
            chunk_content = redactor.redact_text(
                chunk.get("content", ""), profile=raw_profile
            )
            rag_context += (
                f"\n[Tài liệu {idx}]: {chunk.get('section_title', '')} "
                f"(Trích dẫn: {chunk.get('citation', '')})\n{chunk_content}\n"
            )

        care_context_str = ""
        if safe_profile or safe_memory:
            care_context_str = json.dumps(
                {
                    "patient_profile_and_current_care": safe_profile,
                    "conversation_memory": safe_memory,
                },
                ensure_ascii=False,
                default=str,
            )[:24000]

        prompt, indirect_sanitized = build_grounded_prompt(
            rag_context=rag_context,
            user_query=safe_query,
            care_context=care_context_str,
            system_prompt=RAG_SYSTEM_PROMPT,
        )

        working_state = dict(state)
        events = append_guard_event(
            working_state,  # type: ignore[arg-type]
            layer="L4_GENERATION",
            rule_id="PII-REDACTED",
            decision="PASSED",
            detail=(
                f"Đã ẩn danh PII trên hồ sơ, câu hỏi và {len(safe_history)} tin nhắn lịch sử "
                "trước khi gọi LLM."
            ),
        )
        working_state["guard_events"] = events

        if indirect_sanitized:
            events = append_guard_event(
                working_state,  # type: ignore[arg-type]
                layer="L4_GENERATION",
                rule_id="INDIRECT-INJECTION-DEFENSE",
                decision="REWRITTEN",
                detail="Đã loại bỏ chỉ thị điều khiển gián tiếp hoặc thẻ XML giả mạo trong ngữ cảnh.",
            )
            working_state["guard_events"] = events

        raw_output = _invoke_llm_caller(
            llm_caller,
            prompt,
            state.get("model_override"),
            safe_history,
        )
        if not raw_output or not raw_output.strip():
            events = append_guard_event(
                working_state,  # type: ignore[arg-type]
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
            working_state,  # type: ignore[arg-type]
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
