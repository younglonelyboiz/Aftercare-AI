from typing import List, Dict, Any, Optional
from backend.app.rag.retriever.router import QueryRouter
from backend.app.rag.retriever.bm25_search import BM25SearchEngine, tokenize_vietnamese
from backend.app.rag.retriever.reranker import RerankEngine
from backend.app.rag.retriever.pgvector_store import PgVectorStore

class PgVectorRetriever:
    """Retriever Orchestrator điều phối pipeline tìm kiếm 4 tầng:
    
    1. Router: Xác định phân kho câu hỏi (Kho 1 Cấp cứu vs Kho 2 Chăm sóc tại nhà).
    2. Candidate Retrieval: Tìm kiếm song song Dense (PgVector) + Sparse (BM25).
    3. Fusion: Hợp nhất danh sách ứng viên bằng Reciprocal Rank Fusion (RRF).
    4. Reranking: Chấm điểm lại bằng Cross-Encoder (BAAI/bge-reranker-base).
    """

    def __init__(self):
        self.router = QueryRouter()
        self.vector_store = PgVectorStore()
        self.bm25_engine = BM25SearchEngine()
        self.reranker_engine = RerankEngine()

        # Cache in-memory metadata và khởi tạo chỉ mục BM25
        self.chunk_by_id: Dict[str, Dict[str, Any]] = {}
        self._load_corpus()

    def _load_corpus(self):
        chunks = self.vector_store.fetch_all_chunks()
        for c in chunks:
            c["tokens"] = tokenize_vietnamese(c["content"] + " " + (c["section_title"] or ""))
            self.chunk_by_id[c["chunk_id"]] = c
        self.bm25_engine.build_index(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        knowledge_store_filter: Optional[str] = None,
        use_reranker: bool = True
    ) -> List[Dict[str, Any]]:
        """Thực thi pipeline truy vấn thông tin."""
        # 1. Routing
        store = knowledge_store_filter or self.router.route_query_store(query)

        # 2. Candidate Retrieval
        dense_candidates = self.vector_store.search_dense(query, store_filter=store, candidate_k=15)
        query_tokens = tokenize_vietnamese(query)
        bm25_candidates = self.bm25_engine.search(query_tokens, store_filter=store, candidate_k=15)

        # 3. RRF Rank Fusion
        candidate_ids = self.reranker_engine.reciprocal_rank_fusion(
            dense_candidates=dense_candidates,
            bm25_candidates=bm25_candidates,
            k=60,
            top_n=15
        )

        if not candidate_ids:
            return []

        # 4. Cross-Encoder Reranking
        if use_reranker:
            final_scored = self.reranker_engine.rerank(
                query=query,
                candidate_ids=candidate_ids,
                chunk_by_id=self.chunk_by_id,
                top_k=top_k
            )
        else:
            final_scored = [(cid, 1.0) for cid in candidate_ids[:top_k]]

        # 5. Format Output
        results = []
        for cid, score in final_scored:
            c = self.chunk_by_id.get(cid)
            if not c:
                continue
            results.append({
                "chunk_id": c["chunk_id"],
                "content": c["content"],
                "section_title": c["section_title"],
                "citation": c["citation"],
                "safety_tier": c["safety_tier"],
                "knowledge_store": c["knowledge_store"],
                "document_tag": c["document_tag"],
                "document_name": c["document_name"],
                "pdf_page": c["pdf_page"],
                "similarity_score": score
            })

        return results
