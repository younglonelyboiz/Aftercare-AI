"""
Nút truy xuất và kiểm chứng bằng chứng y khoa (L3 Evidence Retrieval & Gate Node) — [W07-T3.1].
"""
from typing import Any, Callable, Dict, List, Optional

from backend.app.guardrails.evidence_gate import EvidenceGate
from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event


def make_retrieve_evidence_node(
    retrieve_fn: Callable[[str, int], List[Dict[str, Any]]],
    top_k: int = 3,
    evidence_gate: Optional[EvidenceGate] = None,
):
    """Tạo nút `retrieve_evidence`: truy xuất top-k đoạn tài liệu và lọc qua cổng `EvidenceGate`."""
    gate = evidence_gate or EvidenceGate()

    @safe_node("retrieve_evidence", layer="L3_EVIDENCE")
    def retrieve_evidence_node(state: AftercareState) -> Dict[str, Any]:
        query = state.get("clean_message") or state.get("raw_message") or ""
        raw_chunks = retrieve_fn(query, top_k) or []

        verdict = gate.evaluate(raw_chunks, query=query)
        if not verdict.evidence_ok:
            events = append_guard_event(
                state,
                layer="L3_EVIDENCE",
                rule_id=verdict.rule_id,
                decision="BLOCKED",
                detail=verdict.detail,
            )
            return {
                "retrieved_chunks": [],
                "citations": [],
                "evidence_ok": False,
                "guard_events": events,
            }

        accepted_chunks = verdict.accepted_chunks
        citations: List[Dict[str, Any]] = []
        for chunk in accepted_chunks:
            pdf_url = (
                f"/api/v1/documents/view/{chunk['document_tag']}#page={chunk['pdf_page']}"
                if chunk.get("pdf_page")
                else None
            )
            score = chunk.get("rerank_score", chunk.get("similarity_score", 0.0))
            citations.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "section_title": chunk["section_title"],
                    "citation": chunk["citation"],
                    "safety_tier": chunk["safety_tier"],
                    "document_tag": chunk.get("document_tag"),
                    "document_name": chunk.get("document_name"),
                    "pdf_page": chunk.get("pdf_page"),
                    "pdf_url": pdf_url,
                    "snippet": chunk.get("content", ""),
                    "similarity_score": score,
                    "rerank_score": score,
                }
            )

        events = append_guard_event(
            state,
            layer="L3_EVIDENCE",
            rule_id=verdict.rule_id,
            decision="PASSED",
            detail=verdict.detail,
        )
        return {
            "retrieved_chunks": accepted_chunks,
            "citations": citations,
            "evidence_ok": True,
            "guard_events": events,
        }

    return retrieve_evidence_node
