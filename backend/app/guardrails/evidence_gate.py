"""
Cổng kiểm chứng bằng chứng y khoa (L3 Evidence Gate) — [W07-T3.1].

Đảm bảo bất biến INV-5 (Evidence-Gated Generation):
- Mọi đoạn tài liệu truy xuất từ kho tri thức phải có `rerank_score >= tau`
  (hoặc `similarity_score >= tau`).
- Nếu không có đoạn tài liệu nào đạt ngưỡng `tau`, đánh dấu `evidence_ok = False`
  để đồ thị điều phối rẽ nhánh trực tiếp sang `no_evidence_response` mà không gọi LLM.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings


def get_chunk_score(chunk: Dict[str, Any]) -> float:
    """Lấy điểm xếp hạng ưu tiên `rerank_score`, dự phòng sang `similarity_score`."""
    raw = chunk.get("rerank_score")
    if raw is None:
        raw = chunk.get("similarity_score", 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class EvidenceGateVerdict:
    """Kết quả đánh giá của cổng bằng chứng y khoa (L3 Evidence Gate)."""

    evidence_ok: bool
    accepted_chunks: List[Dict[str, Any]] = field(default_factory=list)
    rejected_count: int = 0
    total_candidates: int = 0
    max_score: float = 0.0
    threshold: float = 0.35
    rule_id: str = "EVIDENCE-GATE-PASS"
    detail: str = ""


class EvidenceGate:
    """Bộ lọc kiểm chứng bằng chứng dựa trên ngưỡng điểm Cross-Encoder `tau`."""

    def __init__(
        self,
        min_score: Optional[float] = None,
        allow_empty_fallback: bool = False,
    ):
        self.min_score: float = (
            float(min_score)
            if min_score is not None
            else float(getattr(settings, "EVIDENCE_MIN_SCORE", 0.35))
        )
        self.allow_empty_fallback = allow_empty_fallback

    def evaluate(
        self,
        chunks: Optional[List[Dict[str, Any]]],
        query: str = "",
    ) -> EvidenceGateVerdict:
        """Lọc các đoạn tài liệu có điểm `>= min_score` và quyết định `evidence_ok`."""
        candidate_list = list(chunks or [])
        total = len(candidate_list)

        if total == 0:
            if self.allow_empty_fallback:
                return EvidenceGateVerdict(
                    evidence_ok=True,
                    accepted_chunks=[],
                    rejected_count=0,
                    total_candidates=0,
                    max_score=0.0,
                    threshold=self.min_score,
                    rule_id="EVIDENCE-GATE-BYPASS-STUB",
                    detail="Bỏ qua kiểm tra rỗng cho stub kiểm thử đơn vị.",
                )
            return EvidenceGateVerdict(
                evidence_ok=False,
                accepted_chunks=[],
                rejected_count=0,
                total_candidates=0,
                max_score=0.0,
                threshold=self.min_score,
                rule_id="EVIDENCE-GATE-REJECT",
                detail=(
                    f"Truy xuất trả về 0 đoạn tài liệu (ngưỡng tau={self.min_score:.2f}). "
                    "Chuyển sang phản hồi không đủ bằng chứng."
                ),
            )

        accepted: List[Dict[str, Any]] = []
        scores: List[float] = []
        for chunk in candidate_list:
            score = get_chunk_score(chunk)
            scores.append(score)
            if score >= self.min_score:
                normalized_chunk = dict(chunk)
                normalized_chunk.setdefault("rerank_score", score)
                normalized_chunk.setdefault("similarity_score", score)
                accepted.append(normalized_chunk)

        max_score = max(scores) if scores else 0.0
        rejected_count = total - len(accepted)

        if not accepted:
            return EvidenceGateVerdict(
                evidence_ok=False,
                accepted_chunks=[],
                rejected_count=rejected_count,
                total_candidates=total,
                max_score=max_score,
                threshold=self.min_score,
                rule_id="EVIDENCE-GATE-REJECT",
                detail=(
                    f"Không có đoạn tài liệu nào đạt ngưỡng bằng chứng tối thiểu "
                    f"(tau={self.min_score:.2f}, điểm cao nhất={max_score:.4f})."
                ),
            )

        return EvidenceGateVerdict(
            evidence_ok=True,
            accepted_chunks=accepted,
            rejected_count=rejected_count,
            total_candidates=total,
            max_score=max_score,
            threshold=self.min_score,
            rule_id="EVIDENCE-GATE-PASS",
            detail=(
                f"Giữ lại {len(accepted)}/{total} đoạn tài liệu vượt ngưỡng bằng chứng "
                f"(tau={self.min_score:.2f}, điểm cao nhất={max_score:.4f})."
            ),
        )


__all__ = ["EvidenceGate", "EvidenceGateVerdict", "get_chunk_score"]

