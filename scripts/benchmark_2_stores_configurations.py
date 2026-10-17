import json
import re
import psycopg2
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

DB_CONFIG = {
    "dbname": "aftercare_db",
    "user": "postgres",
    "password": "postgrespassword",
    "host": "localhost",
    "port": 5432
}

def tokenize(text):
    # Unigram + Bigram giúp BM25 bắt từ ghép tiếng Việt cực nhạy mà không cần phụ thuộc thư viện ngoài
    words = re.findall(r"\w+", text.lower())
    bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
    return words + bigrams

def dcg_at_k(r, k):
    r = np.asarray(r, dtype=float)[:k]
    if r.size:
        return r[0] + np.sum(r[1:] / np.log2(np.arange(2, r.size + 1)))
    return 0.0

def ndcg_at_k(retrieved_chunk_ids, ground_truth_chunk_ids, k):
    r = [1 if cid in ground_truth_chunk_ids else 0 for cid in retrieved_chunk_ids[:k]]
    actual_dcg = dcg_at_k(r, k)
    ideal_r = [1] * min(len(ground_truth_chunk_ids), k) + [0] * max(0, k - len(ground_truth_chunk_ids))
    ideal_dcg = dcg_at_k(ideal_r, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg

# ==============================================================================
# SMART ROUTER 2 KHO
# ==============================================================================
EMERGENCY_KEYWORDS = [
    "cấp cứu", "115", "nguy kịch", "đe dọa tính mạng", "ngủ gà", "lơ mơ", 
    "lồng ngực im lặng", "im phăng phắc", "ngồi chồm", "ngồi cúi", "nói từng từ",
    "vùng đỏ", "pef dưới 60", "tụt sâu", "ngừng thở", "cắt cơn cấp tốc", "nửa đêm",
    "prednisolone", "viên prednisolone", "đợt cấp"
]

CARE_KEYWORDS = [
    "duy trì", "ngưng bình", "dừng thuốc", "súc miệng", "rát họng", "nấm", "khàn", 
    "run tay", "buồng đệm", "spacer", "tập gym", "chạy bộ", "gắng sức", "vắc xin", "vắc-xin",
    "tiêm phòng", "mang thai", "em bé", "aspirin", "ibuprofen", "dạ dày", "ợ chua",
    "tái khám", "cốp xe", "bảo quản", "viêm mũi", "copd", "chó mèo", "khói thuốc"
]

def route_query_store(query_text):
    q = query_text.lower()
    
    match_emergency = sum(1 for kw in EMERGENCY_KEYWORDS if kw in q)
    match_care = sum(1 for kw in CARE_KEYWORDS if kw in q)
    
    if match_emergency > 0 and match_care > 0:
        return "ALL"
    if match_emergency == 0 and match_care == 0:
        return "ALL"
    
    if match_emergency > 0:
        return "KHO_1_CANH_BAO_CO_DO_CAP_CUU"
    else:
        return "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI"

def run_benchmark():
    print("Connecting to PostgreSQL and loading 192 chunks...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT chunk_id, content, embedding, knowledge_store FROM medical_knowledge_chunks;")
    rows = cur.fetchall()

    all_chunks = []
    chunk_by_id = {}
    for r in rows:
        cid, content, emb_raw, store = r[0], r[1], r[2], r[3]
        if isinstance(emb_raw, str):
            emb = [float(x) for x in emb_raw.strip("[]").split(",")]
        else:
            emb = list(emb_raw)
        
        c_obj = {
            "chunk_id": cid,
            "content": content,
            "embedding": np.array(emb, dtype=np.float32),
            "store": store,
            "tokens": tokenize(content)
        }
        all_chunks.append(c_obj)
        chunk_by_id[cid] = c_obj

    print(f"Loaded {len(all_chunks)} chunks.")
    kho1_chunks = [c for c in all_chunks if c["store"] == "KHO_1_CANH_BAO_CO_DO_CAP_CUU"]
    kho2_chunks = [c for c in all_chunks if c["store"] == "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI"]
    print(f"-> Kho 1 (Cấp cứu): {len(kho1_chunks)} chunks")
    print(f"-> Kho 2 (Chăm sóc): {len(kho2_chunks)} chunks")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nLoading BAAI/bge-m3 embedder on {device}...")
    embedder = SentenceTransformer("BAAI/bge-m3", device=device)
    
    print(f"Loading BAAI/bge-reranker-base on {device}...")
    reranker = CrossEncoder("BAAI/bge-reranker-base", device=device)

    # Đọc golden dataset
    with open("Data/golden_dataset.json", "r", encoding="utf-8") as f:
        golden_dataset = json.load(f)

    configs = [
        "1. Baseline: Dense Vector Toàn Kho",
        "2. Phân Hệ: Router 2 Kho (Dense)",
        "3. Phân Hệ: Router 2 Kho (Hybrid RRF)",
        "4. Phân Hệ: Router 2 Kho + Rerank 🏆"
    ]
    
    metrics_by_config = {cfg: {
        "hit@1": [], "hit@3": [], "hit@5": [],
        "strict_recall@1": [], "strict_recall@3": [], "strict_recall@5": [], "strict_recall@10": [],
        "suff_recall@1": [], "suff_recall@3": [], "suff_recall@5": [], "suff_recall@10": [],
        "precision@1": [], "precision@3": [], "precision@5": [],
        "mrr@1": [], "mrr@3": [], "mrr@5": [],
        "ndcg@1": [], "ndcg@3": [], "ndcg@5": []
    } for cfg in configs}

    print("\nChạy Benchmark 20 test cases trên 4 Cấu hình (Chuẩn IR: Strict Recall & Sufficiency Recall)...")

    for item in golden_dataset:
        query = item["patient_query"]
        gt_chunks = set(item["ground_truth_chunk_ids"])
        retrieval_type = item.get("retrieval_type", "EQUIVALENT")
        
        # Router quyết định kho
        routed_store = route_query_store(query)
        if routed_store == "KHO_1_CANH_BAO_CO_DO_CAP_CUU":
            domain_chunks = kho1_chunks
        elif routed_store == "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI":
            domain_chunks = kho2_chunks
        else: # "ALL"
            domain_chunks = all_chunks

        query_vec = embedder.encode(query, normalize_embeddings=True)
        query_tokens = tokenize(query)

        # --- CẤU HÌNH 1: Baseline Dense Toàn Kho ---
        scores_c1 = []
        for c in all_chunks:
            cosine_sim = float(np.dot(query_vec, c["embedding"]))
            scores_c1.append((c["chunk_id"], cosine_sim))
        scores_c1.sort(key=lambda x: x[1], reverse=True)
        retrieved_c1 = [x[0] for x in scores_c1[:10]]

        # --- CẤU HÌNH 2: Phân Hệ (Dense) qua Router 2 Kho ---
        scores_c2 = []
        for c in domain_chunks:
            cosine_sim = float(np.dot(query_vec, c["embedding"]))
            scores_c2.append((c["chunk_id"], cosine_sim))
        scores_c2.sort(key=lambda x: x[1], reverse=True)
        retrieved_c2 = [x[0] for x in scores_c2[:10]]

        # --- CẤU HÌNH 3: Phân Hệ (Hybrid Dense + Bigram BM25 qua RRF) ---
        bm25 = BM25Okapi([c["tokens"] for c in domain_chunks])
        bm25_scores = bm25.get_scores(query_tokens)

        dense_ranked = sorted(domain_chunks, key=lambda c: float(np.dot(query_vec, c["embedding"])), reverse=True)
        bm25_ranked = sorted(range(len(domain_chunks)), key=lambda idx: bm25_scores[idx], reverse=True)

        dense_rank_dict = {c["chunk_id"]: rank for rank, c in enumerate(dense_ranked, start=1)}
        bm25_rank_dict = {domain_chunks[idx]["chunk_id"]: rank for rank, idx in enumerate(bm25_ranked, start=1)}

        rrf_scores = {}
        for c in domain_chunks:
            cid = c["chunk_id"]
            d_rank = dense_rank_dict[cid]
            b_rank = bm25_rank_dict[cid]
            rrf_scores[cid] = (1.0 / (60 + d_rank)) + (1.0 / (60 + b_rank))

        sorted_c3 = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        retrieved_c3 = [x[0] for x in sorted_c3[:10]]

        # --- CẤU HÌNH 4: Phân Hệ + Rerank (Cross-Encoder) ---
        # Lấy Top 15 ứng viên từ Hybrid C3, predict với batch_size=4 để an toàn tuyệt đối trên GPU 4GB
        candidate_ids = [x[0] for x in sorted_c3[:15]]
        pairs = [[query, chunk_by_id[cid]["content"]] for cid in candidate_ids]
        rerank_scores = reranker.predict(pairs, batch_size=4)
        
        reranked = sorted(zip(candidate_ids, rerank_scores), key=lambda x: x[1], reverse=True)
        retrieved_c4 = [x[0] for x in reranked[:10]]

        # Tính metrics
        for cfg_name, retrieved_ids in [
            ("1. Baseline: Dense Vector Toàn Kho", retrieved_c1),
            ("2. Phân Hệ: Router 2 Kho (Dense)", retrieved_c2),
            ("3. Phân Hệ: Router 2 Kho (Hybrid RRF)", retrieved_c3),
            ("4. Phân Hệ: Router 2 Kho + Rerank 🏆", retrieved_c4)
        ]:
            m = metrics_by_config[cfg_name]
            for k in [1, 3, 5]:
                top_k = set(retrieved_ids[:k])
                hits = top_k.intersection(gt_chunks)
                m[f"hit@{k}"].append(1.0 if len(hits) > 0 else 0.0)
                m[f"precision@{k}"].append(len(hits) / k)
                
                first_rank = 0
                for rank, cid in enumerate(retrieved_ids[:k], start=1):
                    if cid in gt_chunks:
                        first_rank = rank
                        break
                m[f"mrr@{k}"].append(1.0 / first_rank if first_rank > 0 else 0.0)
                m[f"ndcg@{k}"].append(ndcg_at_k(retrieved_ids, gt_chunks, k))

            for k in [1, 3, 5, 10]:
                top_k = set(retrieved_ids[:k])
                hits = top_k.intersection(gt_chunks)
                # 1. Strict Recall: Yêu cầu lấy đủ 100% chunks gán
                m[f"strict_recall@{k}"].append(len(hits) / len(gt_chunks) if len(gt_chunks) > 0 else 0.0)
                # 2. Sufficiency Recall (DPR / Top-K Accuracy): Nếu là EQUIVALENT, có ít nhất 1 chunk là đủ bằng chứng 100%
                if retrieval_type == "EQUIVALENT":
                    m[f"suff_recall@{k}"].append(1.0 if len(hits) >= 1 else 0.0)
                else:
                    m[f"suff_recall@{k}"].append(len(hits) / len(gt_chunks) if len(gt_chunks) > 0 else 0.0)

    # In Bảng đối soát 4 cấu hình
    print("\n" + "=" * 130)
    print("BẢNG TỔNG HỢP SO SÁNH 4 CẤU HÌNH THỰC NGHIỆM IR (ROUTER 2 KHO + ALL FALLBACK)")
    print("=" * 130)
    header = f"{'Chỉ số (Metric)':<26} | {'1. Baseline (Dense)':<20} | {'2. Phân Hệ (Dense)':<20} | {'3. Phân Hệ (Hybrid)':<22} | {'4. Phân Hệ + Rerank 🏆':<22}"
    print(header)
    print("-" * 130)

    def fmt_pct(val): return f"{np.mean(val)*100:.1f}%"
    def fmt_num(val): return f"{np.mean(val):.3f}"

    rows_def = [
        ("Hit Rate@1", "hit@1", fmt_pct),
        ("Hit Rate@3", "hit@3", fmt_pct),
        ("Hit Rate@5", "hit@5", fmt_pct),
        ("---", "---", None),
        ("Sufficiency Recall@1", "suff_recall@1", fmt_pct),
        ("Sufficiency Recall@3", "suff_recall@3", fmt_pct),
        ("Sufficiency Recall@5", "suff_recall@5", fmt_pct),
        ("Sufficiency Recall@10", "suff_recall@10", fmt_pct),
        ("---", "---", None),
        ("Strict Recall@1", "strict_recall@1", fmt_pct),
        ("Strict Recall@3", "strict_recall@3", fmt_pct),
        ("Strict Recall@5", "strict_recall@5", fmt_pct),
        ("Strict Recall@10", "strict_recall@10", fmt_pct),
        ("---", "---", None),
        ("Precision@1", "precision@1", fmt_pct),
        ("Precision@3", "precision@3", fmt_pct),
        ("Precision@5", "precision@5", fmt_pct),
        ("---", "---", None),
        ("MRR@1", "mrr@1", fmt_num),
        ("MRR@3", "mrr@3", fmt_num),
        ("MRR@5", "mrr@5", fmt_num),
        ("---", "---", None),
        ("NDCG@1", "ndcg@1", fmt_num),
        ("NDCG@3", "ndcg@3", fmt_num),
        ("NDCG@5", "ndcg@5", fmt_num),
    ]

    for label, key, func in rows_def:
        if label == "---":
            print("-" * 130)
            continue
        c1 = func(metrics_by_config["1. Baseline: Dense Vector Toàn Kho"][key])
        c2 = func(metrics_by_config["2. Phân Hệ: Router 2 Kho (Dense)"][key])
        c3 = func(metrics_by_config["3. Phân Hệ: Router 2 Kho (Hybrid RRF)"][key])
        c4 = func(metrics_by_config["4. Phân Hệ: Router 2 Kho + Rerank 🏆"][key])
        print(f"{label:<26} | {c1:<20} | {c2:<20} | {c3:<22} | {c4:<22}")

    print("=" * 130)

if __name__ == "__main__":
    run_benchmark()
