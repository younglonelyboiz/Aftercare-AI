import re
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

def tokenize_vietnamese(text: str) -> List[str]:
    """Tokenize văn bản tiếng Việt kết hợp Unigram và Bigram để tối ưu BM25."""
    words = re.findall(r"\w+", text.lower())
    bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)]
    return words + bigrams

class BM25SearchEngine:
    """Quản lý chỉ mục và tìm kiếm từ khóa BM25 Okapi theo từng phân kho."""

    def __init__(self):
        self.bm25_indices: Dict[str, BM25Okapi] = {}
        self.corpus_chunks: Dict[str, List[Dict[str, Any]]] = {}

    def build_index(self, all_chunks: List[Dict[str, Any]]):
        """Khởi tạo chỉ mục BM25 cho toàn kho và từng phân kho."""
        self.corpus_chunks["ALL"] = all_chunks
        self.corpus_chunks["KHO_1_CANH_BAO_CO_DO_CAP_CUU"] = [
            c for c in all_chunks if c["knowledge_store"] == "KHO_1_CANH_BAO_CO_DO_CAP_CUU"
        ]
        self.corpus_chunks["KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI"] = [
            c for c in all_chunks if c["knowledge_store"] == "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI"
        ]

        for store_key, c_list in self.corpus_chunks.items():
            if c_list:
                tokenized_corpus = [c["tokens"] for c in c_list]
                self.bm25_indices[store_key] = BM25Okapi(tokenized_corpus)

    def search(
        self, query_tokens: List[str], store_filter: Optional[str] = None, candidate_k: int = 15
    ) -> List[Dict[str, Any]]:
        """Truy xuất danh sách chunk_id theo điểm BM25."""
        target_store = store_filter if store_filter in self.bm25_indices else "ALL"
        bm25 = self.bm25_indices.get(target_store)
        chunk_pool = self.corpus_chunks.get(target_store, [])

        if not bm25 or not chunk_pool:
            return []

        doc_scores = bm25.get_scores(query_tokens)
        top_indices = np.argsort(doc_scores)[::-1][:candidate_k]

        results = []
        for idx in top_indices:
            score = float(doc_scores[idx])
            if score > 0.0:
                results.append({"chunk_id": chunk_pool[idx]["chunk_id"], "bm25_score": score})
        return results
