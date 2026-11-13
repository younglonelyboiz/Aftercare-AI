"""
Xây dựng đồ thị điều phối LangGraph StateGraph ("Guarded Deterministic Graph") — [W07-T1.5].

Toàn bộ quyết định chuyển nút là hàm Python tất định trong `routing.py`.
Nút `generate_answer` là nút duy nhất được phép gọi LLM và chỉ có thể đạt tới khi:
`risk_level == "NORMAL"` VÀ `session_locked_red == False` VÀ `policy_decision == "ALLOW"` VÀ `evidence_ok == True`.
"""
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from backend.app.orchestration.nodes import (
    make_action_plan_response_node,
    make_audit_node,
    make_emergency_response_node,
    make_finalize_node,
    make_generate_answer_node,
    make_load_context_node,
    make_no_evidence_response_node,
    make_output_guard_node,
    make_policy_guard_node,
    make_retrieve_evidence_node,
    make_safe_fallback_node,
    make_safe_refusal_node,
    make_safety_triage_node,
    make_sanitize_input_node,
    make_session_lock_check_node,
)
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
from backend.app.orchestration.state import AftercareState


def build_aftercare_graph(
    profile_loader: Callable[[str], Dict[str, Any]],
    screener_fn: Callable[[str, Dict[str, Any]], Any],
    retrieve_fn: Callable[[str, int], List[Dict[str, Any]]],
    llm_caller: Callable[[str, Optional[str]], Optional[str]],
    policy_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
    output_evaluator: Optional[Callable[[AftercareState], Dict[str, Any]]] = None,
    evidence_gate: Optional[Any] = None,
    top_k: int = 3,
):
    """Khởi tạo và biên dịch `StateGraph` cho luồng hội thoại Aftercare-AI."""
    workflow = StateGraph(AftercareState)

    # 1. Đăng ký các nút chuyên trách
    workflow.add_node("load_context", make_load_context_node(profile_loader))
    workflow.add_node("sanitize_input", make_sanitize_input_node())
    workflow.add_node("safety_triage", make_safety_triage_node(screener_fn))
    workflow.add_node("session_lock_check", make_session_lock_check_node())
    workflow.add_node("policy_guard", make_policy_guard_node(policy_evaluator))
    workflow.add_node(
        "retrieve_evidence",
        make_retrieve_evidence_node(
            retrieve_fn, top_k=top_k, evidence_gate=evidence_gate
        ),
    )
    workflow.add_node("generate_answer", make_generate_answer_node(llm_caller))
    workflow.add_node("output_guard", make_output_guard_node(output_evaluator))

    # Các nút phản hồi tất định (không gọi LLM)
    workflow.add_node("emergency_response", make_emergency_response_node())
    workflow.add_node("action_plan_response", make_action_plan_response_node())
    workflow.add_node("safe_refusal", make_safe_refusal_node())
    workflow.add_node("no_evidence_response", make_no_evidence_response_node())
    workflow.add_node("safe_fallback", make_safe_fallback_node())

    # Nút hoàn tất và kiểm toán
    workflow.add_node("finalize", make_finalize_node())
    workflow.add_node("audit", make_audit_node())

    # 2. Kết nối các cạnh tất định
    workflow.add_edge(START, "load_context")
    workflow.add_conditional_edges(
        "load_context",
        route_after_load_context,
        {
            "sanitize_input": "sanitize_input",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "sanitize_input",
        route_after_sanitize,
        {
            "safety_triage": "safety_triage",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "safety_triage",
        route_after_triage,
        {
            "emergency_response": "emergency_response",
            "action_plan_response": "action_plan_response",
            "session_lock_check": "session_lock_check",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "session_lock_check",
        route_after_session_lock,
        {
            "emergency_response": "emergency_response",
            "policy_guard": "policy_guard",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "policy_guard",
        route_after_policy,
        {
            "safe_refusal": "safe_refusal",
            "retrieve_evidence": "retrieve_evidence",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "retrieve_evidence",
        route_after_retrieve,
        {
            "no_evidence_response": "no_evidence_response",
            "generate_answer": "generate_answer",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "generate_answer",
        route_after_generate,
        {
            "output_guard": "output_guard",
            "safe_fallback": "safe_fallback",
        },
    )
    workflow.add_conditional_edges(
        "output_guard",
        route_after_output_guard,
        {
            "finalize": "finalize",
            "action_plan_response": "action_plan_response",
            "safe_fallback": "safe_fallback",
        },
    )

    # Mọi nhánh kết thúc đều hội tụ về `finalize` -> `audit` -> `END` (INV-7)
    workflow.add_edge("emergency_response", "finalize")
    workflow.add_edge("action_plan_response", "finalize")
    workflow.add_edge("safe_refusal", "finalize")
    workflow.add_edge("no_evidence_response", "finalize")
    workflow.add_edge("safe_fallback", "finalize")
    workflow.add_edge("finalize", "audit")
    workflow.add_edge("audit", END)

    return workflow.compile()

