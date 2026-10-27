from typing import List, Dict, Tuple, Any
import torch
from sentence_transformers import CrossEncoder
from backend.app.core.config import settings

class RerankEngine:
    """Quản lý mô hình Cross-Encoder để tái chấm điểm chính xác và xếp hạng RRF."""

    def __init__(self):
        device = "cuda" if (settings.RERANKER_DEVICE == "cuda" and torch.cuda.is_available()) else "cpu"
        self.reranker = CrossEncoder(settings.RERANKER_MODEL, device=device)

    @staticmethod
    def reciprocal_rank_fusion(
        dense_candidates: List[Dict[str, Any]],
        bm25_candidates: List[Dict[str, Any]],
        k: int = 60,
        top_n: int = 15
    ) -> List[str]:
        """Hợp nhất xếp hạng Dense và BM25 dựa trên thứ hạng (Rank-based), tránh scale mismatch."""
        rrf_scores: Dict[str, float] = {}

        for rank, item in enumerate(dense_candidates, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

        for rank, item in enumerate(bm25_candidates, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

        sorted_by_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in sorted_by_rrf[:top_n]]

    def rerank(
        self,
        query: str,
        candidate_ids: List[str],
        chunk_by_id: Dict[str, Dict[str, Any]],
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """Sử dụng Cross-Encoder để chấm điểm cặp (query, document) và lấy top_k."""
        if not candidate_ids:
            return []

        if len(candidate_ids) == 1:
            return [(candidate_ids[0], 1.0)]

        pairs = [[query, chunk_by_id[cid]["content"]] for cid in candidate_ids]
        scores = self.reranker.predict(pairs, batch_size=4)
        reranked = sorted(zip(candidate_ids, scores), key=lambda x: x[1], reverse=True)
        return [(cid, float(score)) for cid, score in reranked[:top_k]]
