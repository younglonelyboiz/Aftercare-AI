"""
Kịch bản hiệu chỉnh ngưỡng cổng bằng chứng (Evidence Gate Calibration) — [W07-T3.2].

Đánh giá ngưỡng điểm `tau` (`EVIDENCE_MIN_SCORE`) trên:
- 20 câu hỏi trong phạm vi tài liệu (In-Corpus) lấy từ `Data/golden_dataset.json`.
- 20 câu hỏi y tế ngoài phạm vi tài liệu Hen phế quản (Out-of-Corpus).

Quét dải ngưỡng `tau` từ 0.05 đến 0.85, tính Precision, Recall, F1-score,
Tỷ lệ chặn nhầm (False Reject Rate) và Tỷ lệ lọt câu ngoài tài liệu (False Accept Rate),
sau đó xuất kết quả ra `Evidence/W07/evidence_gate_calibration.json`.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.guardrails.evidence_gate import EvidenceGate  # noqa: E402

GOLDEN_DATASET_PATH = ROOT_DIR / "Data" / "golden_dataset.json"
CALIBRATION_REPORT_PATH = (
    ROOT_DIR / "Evidence" / "W07" / "evidence_gate_calibration.json"
)

# 20 câu hỏi y khoa ngoài tài liệu hướng dẫn Hen phế quản (nhãn kỳ vọng: evidence_ok = False)
OUT_OF_CORPUS_QUERIES: List[str] = [
    "Lịch tiêm vắc xin viêm gan B cho trẻ sơ sinh trong 24 giờ đầu sau sinh như thế nào?",
    "Chế độ ăn giảm purin cho bệnh nhân bị bệnh gút cấp tính gồm những thực phẩm nào?",
    "Cách thay băng vết mổ nội soi tái tạo dây chằng chéo trước khớp gối tại nhà?",
    "Chỉ số HbA1c mục tiêu ở người bệnh đái tháo đường típ 2 cao tuổi là bao nhiêu?",
    "Hướng dẫn tập vật lý trị liệu phục hồi chức năng sau tai biến mạch máu não?",
    "Phác đồ bù dịch Oresol theo cân nặng cho trẻ tiêu chảy cấp mất nước mức độ vừa?",
    "Bệnh nhân suy thận mạn giai đoạn 4 lọc máu chu kỳ cần hạn chế kali như thế nào?",
    "Cách theo dõi vết thương sau phẫu thuật cắt túi mật nội soi tại nhà?",
    "Triệu chứng điển hình của cơn đau quặn thận do sỏi niệu quản là gì?",
    "Cách tự khám vú định kỳ hàng tháng để tầm soát sớm ung thư vú?",
    "Hướng dẫn chăm sóc răng miệng sau khi nhổ răng khôn hàm dưới lệch ngầm?",
    "Chế độ dinh dưỡng hạn chế muối cho người bệnh suy tim phân suất tống máu giảm?",
    "Cách xử trí hạ đường huyết nhẹ tại nhà bằng nguyên tắc 15-15 cho người tiểu đường?",
    "Lịch khám thai định kỳ trong 3 tháng cuối thai kỳ gồm những xét nghiệm nào?",
    "Cách vệ sinh mắt sau phẫu thuật thay thủy tinh thể nhân tạo Phaco?",
    "Hướng dẫn tập xoay khớp vai điều trị viêm quanh khớp vai thể đông cứng?",
    "Người bệnh suy giáp sau cắt tuyến giáp cần uống Levothyroxine vào thời điểm nào?",
    "Dấu hiệu nhận biết sớm biến chứng bàn chân đái tháo đường và cách chọn giày dép?",
    "Chế độ ăn nhiều chất xơ và cách ngâm hậu môn bằng nước ấm cho người bệnh trĩ?",
    "Cách chăm sóc da cho trẻ nhỏ bị viêm da cơ địa dị ứng mùa hanh khô?",
]


def load_in_corpus_queries(limit: int = 20) -> List[str]:
    """Đọc 20 câu hỏi chuẩn trong phạm vi tài liệu từ `Data/golden_dataset.json`."""
    data = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
    queries = [
        str(item.get("patient_query") or item.get("query") or "").strip()
        for item in data
        if item.get("patient_query") or item.get("query")
    ]
    return queries[:limit]


def score_queries_cross_encoder(
    in_queries: List[str], out_queries: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Chấm điểm thực tế bằng BM25 + CrossEncoder (`BAAI/bge-reranker-base`) trên 192 đoạn tài liệu trong PostgreSQL."""
    from sentence_transformers import CrossEncoder
    from backend.app.rag.retriever.bm25_search import BM25SearchEngine, tokenize_vietnamese
    from backend.app.core.database import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT chunk_id, section_title, content, knowledge_store FROM medical_knowledge_chunks")
        ).mappings().all()

    chunks: List[Dict[str, Any]] = []
    chunk_by_id: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        item = dict(r)
        item["tokens"] = tokenize_vietnamese(
            (item.get("content") or "") + " " + (item.get("section_title") or "")
        )
        chunks.append(item)
        chunk_by_id[item["chunk_id"]] = item

    bm25 = BM25SearchEngine()
    bm25.build_index(chunks)
    ce = CrossEncoder("BAAI/bge-reranker-base", device="cpu")

    def _score_list(queries: List[str], label: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for q in queries:
            q_tokens = tokenize_vietnamese(q)
            cands = bm25.search(q_tokens, store_filter=None, candidate_k=5)
            if not cands:
                cands = chunks[:3]
            pairs = [[q, chunk_by_id[c["chunk_id"]]["content"]] for c in cands]
            raw_scores = ce.predict(pairs, batch_size=5)
            scores = (
                [float(raw_scores)]
                if isinstance(raw_scores.tolist(), (int, float))
                else [float(s) for s in raw_scores.tolist()]
            )
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            results.append(
                {
                    "query": q,
                    "label": label,
                    "max_score": round(float(scores[best_idx]), 6),
                    "top_chunk_id": cands[best_idx]["chunk_id"],
                }
            )
        return results

    return {
        "in_corpus": _score_list(in_queries, label=1),
        "out_of_corpus": _score_list(out_queries, label=0),
    }


def evaluate_threshold_curve(
    scored_in: List[Dict[str, Any]],
    scored_out: List[Dict[str, Any]],
    thresholds: List[float],
) -> List[Dict[str, Any]]:
    """Tính Precision, Recall, F1, False Reject Rate và False Accept Rate trên dải ngưỡng `tau`."""
    curve: List[Dict[str, Any]] = []
    for tau in thresholds:
        gate = EvidenceGate(min_score=tau)
        tp = sum(
            1
            for item in scored_in
            if gate.evaluate([{"rerank_score": item["max_score"]}]).evidence_ok
        )
        fn = len(scored_in) - tp
        fp = sum(
            1
            for item in scored_out
            if gate.evaluate([{"rerank_score": item["max_score"]}]).evidence_ok
        )
        tn = len(scored_out) - fp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        false_reject_rate = fn / len(scored_in) if scored_in else 0.0
        false_accept_rate = fp / len(scored_out) if scored_out else 0.0

        curve.append(
            {
                "tau": round(tau, 2),
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "tn": tn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "false_reject_rate": round(false_reject_rate, 4),
                "false_accept_rate": round(false_accept_rate, 4),
            }
        )
    return curve


def run_calibration(live: bool = True) -> Dict[str, Any]:
    in_queries = load_in_corpus_queries(limit=20)
    out_queries = list(OUT_OF_CORPUS_QUERIES[:20])

    if live:
        scored = score_queries_cross_encoder(in_queries, out_queries)
    else:
        raise RuntimeError("Cần chạy với --live để chấm điểm bằng CrossEncoder.")

    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80]
    curve = evaluate_threshold_curve(
        scored["in_corpus"], scored["out_of_corpus"], thresholds
    )

    # Chọn ngưỡng tau tối ưu hóa F1 (ưu tiên ngưỡng gần 0.35 khi F1 bằng nhau)
    best_point = max(
        curve,
        key=lambda row: (row["f1"], -abs(row["tau"] - 0.35)),
    )

    report = {
        "in_corpus_count": len(scored["in_corpus"]),
        "out_of_corpus_count": len(scored["out_of_corpus"]),
        "selected_tau": best_point["tau"],
        "configured_default_tau": 0.35,
        "best_metrics": best_point,
        "threshold_curve": curve,
        "samples": scored,
    }
    CALIBRATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", default=True)
    args = parser.parse_args()
    result = run_calibration(live=args.live)
    print(
        f"Calibration complete: selected_tau={result['selected_tau']}, "
        f"F1={result['best_metrics']['f1']}, "
        f"Precision={result['best_metrics']['precision']}, "
        f"Recall={result['best_metrics']['recall']}"
    )
