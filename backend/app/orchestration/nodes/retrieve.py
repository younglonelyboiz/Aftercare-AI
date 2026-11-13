"""
Nút truy xuất bằng chứng y khoa (L3 Evidence Retrieval Node).
"""
from typing import Any, Callable, Dict, List

from backend.app.orchestration.safe_node import safe_node
from backend.app.orchestration.state import AftercareState, append_guard_event


def make_retrieve_evidence_node(
    retrieve_fn: Callable[[str, int], List[Dict[str, Any]]],
    top_k: int = 3,
):
    """Tạo nút `retrieve_evidence`: truy xuất top-k đoạn tài liệu và chuẩn hóa trích dẫn."""

    @safe_node("retrieve_evidence", layer="L3_EVIDENCE")
    def retrieve_evidence_node(state: AftercareState) -> Dict[str, Any]:
        query = state.get("clean_message") or state.get("raw_message") or ""
        retrieved_chunks = retrieve_fn(query, top_k) or []

        citations: List[Dict[str, Any]] = []
        for chunk in retrieved_chunks:
            pdf_url = (
                f"/api/v1/documents/view/{chunk['document_tag']}#page={chunk['pdf_page']}"
                if chunk.get("pdf_page")
                else None
            )
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
                    "similarity_score": chunk["similarity_score"],
                }
            )

        events = append_guard_event(
            state,
            layer="L3_EVIDENCE",
            rule_id="EVIDENCE-RETRIEVED",
            decision="PASSED",
            detail=f"Đã truy xuất {len(retrieved_chunks)} đoạn tài liệu y khoa.",
        )
        return {
            "retrieved_chunks": retrieved_chunks,
            "citations": citations,
            "evidence_ok": True,
            "guard_events": events,
        }

    return retrieve_evidence_node

