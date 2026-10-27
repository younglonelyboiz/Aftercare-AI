import sys
import json
import time
import os
from pathlib import Path

# Tự động đưa thư mục gốc của dự án vào sys.path (không cần gõ PYTHONPATH=.)
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from typing import List, Dict, Any
import numpy as np
from openai import OpenAI
from google import genai

from backend.app.core.config import settings
from backend.app.rag.retriever import PgVectorRetriever
from backend.app.rag.prompts import RAG_SYSTEM_PROMPT, PROMPT_TEMPLATE

GOLDEN_DATASET_PATH = BASE_DIR / "Data" / "golden_dataset.json"

# ==============================================================================
# 1. CÁC PROMPT GIÁM KHẢO (JUDGE PROMPTS) TỐI ƯU RIÊNG CHO TIẾNG VIỆT Y KHOA
# ==============================================================================

FAITHFULNESS_PROMPT_VN = """Bạn là giám khảo thẩm định độ trung thực (Faithfulness) y khoa.
Nhiệm vụ: Đánh giá câu trả lời của AI có bám sát TÀI LIỆU hay bị bịa đặt/ảo giác.

TÀI LIỆU:
{context}

CÂU TRẢ LỜI CỦA AI:
{answer}

QUY TẮC:
- Bỏ qua lời chào hỏi, xưng hô và câu dặn tái khám thông thường.
- Chấp nhận từ đồng nghĩa y khoa tiếng Việt (bình xịt = bình hít, cắt cơn = giảm triệu chứng).
- Cho điểm 0.0 đến 1.0 (1.0 = bám sát tài liệu 100%; dưới 0.5 = bịa thông tin y tế sai lệch).

Trả về JSON:
{{"score": 1.0, "reason": "giải thích ngắn gọn trong 1 câu"}}
"""

ANSWER_RELEVANCE_PROMPT_VN = """Bạn là giám khảo chấm độ liên quan lâm sàng (Answer Relevance).
Nhiệm vụ: Đánh giá câu trả lời của AI có trả lời đúng trọng tâm câu hỏi của người bệnh hay không.

CÂU HỎI CỦA BỆNH NHÂN:
{question}

ĐÁP ÁN CHUẨN LÂM SÀNG:
{ground_truth}

CÂU TRẢ LỜI CỦA AI:
{answer}

QUY TẮC:
- Cho điểm 0.0 đến 1.0 (0.8 - 1.0 = trả lời thẳng thắc mắc và đủ ý chính của Đáp án chuẩn; dưới 0.5 = lạc đề hoặc né tránh câu hỏi).

Trả về JSON:
{{"score": 0.95, "reason": "giải thích ngắn gọn trong 1 câu"}}
"""


class VietnameseRagasEvaluator:
    def __init__(self):
        print("Đang khởi tạo Retriever và Judge LLM Client...")
        self.retriever = PgVectorRetriever()

        # Judge Client: Ưu tiên OpenRouter (GPT-4o), dự phòng Gemini
        self.openrouter_client = (
            OpenAI(
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=settings.OPENROUTER_API_KEY,
            )
            if settings.OPENROUTER_API_KEY
            else None
        )
        self.gemini_client = (
            genai.Client(api_key=settings.GEMINI_API_KEY)
            if settings.GEMINI_API_KEY
            else None
        )

        # Model Cấu hình qua OpenRouter:
        self.generator_model = "google/gemini-2.5-flash"  # Mô hình trả lời
        self.judge_model = "openai/gpt-4o"               # Mô hình giám khảo

    def _call_judge_llm(self, prompt: str) -> Dict[str, Any]:
        """Gọi Judge Model (openai/gpt-4o qua OpenRouter) và parse JSON (có auto-retry khi gặp 402 in-flight)."""
        if not self.openrouter_client:
            return {"score": 0.0, "comment": "Chưa cấu hình OPENROUTER_API_KEY"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                res = self.openrouter_client.chat.completions.create(
                    model=self.judge_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=400,
                    temperature=0.1,
                )
                content = res.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                err_str = str(e)
                if "402" in err_str or "in_flight" in err_str or "429" in err_str:
                    wait_sec = 6 * (attempt + 1)
                    print(f"  ⏳ [OpenRouter in-flight limit]: Đang chờ {wait_sec}s rồi tự động thử lại (Lần {attempt+1}/{max_retries})...")
                    time.sleep(wait_sec)
                else:
                    print(f"[Judge OpenRouter Error ({self.judge_model})]: {e}")
                    break

        return {"score": 0.0, "reason": "Lỗi OpenRouter rate limit / in-flight budget"}

    def _generate_answer(self, query: str, context_text: str) -> str:
        """Sinh câu trả lời từ Mô hình lâm sàng (google/gemini-2.5-flash qua OpenRouter)."""
        prompt = PROMPT_TEMPLATE.format(
            system_prompt=RAG_SYSTEM_PROMPT,
            rag_context=context_text,
            user_query=query,
        )

        if not self.openrouter_client:
            return "Chưa cấu hình OPENROUTER_API_KEY."

        try:
            res = self.openrouter_client.chat.completions.create(
                model=self.generator_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
            )
            return res.choices[0].message.content or ""
        except Exception as e:
            return f"Lỗi sinh câu trả lời từ OpenRouter ({self.generator_model}): {e}"

    def evaluate_testset(self, test_cases_list: List[Dict[str, Any]] = None, limit: int = None):
        if test_cases_list is not None:
            test_cases = test_cases_list
        else:
            with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
                test_cases = json.load(f)

        if limit:
            test_cases = test_cases[:limit]

        print(f"\n🚀 BẮT ĐẦU ĐÁNH GIÁ RAGAS TRÊN {len(test_cases)} TEST CASES (GOLDEN DATASET)")
        print("=" * 100)

        output_file = BASE_DIR / "reports" / "ragas_benchmark_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Đọc dữ liệu cũ nếu có để cộng dồn/resume
        existing_results_map: Dict[str, Dict[str, Any]] = {}
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    for item in old_data.get("details", []):
                        if "test_case_id" in item:
                            existing_results_map[item["test_case_id"]] = item
                if existing_results_map:
                    print(f"📦 Đã tìm thấy {len(existing_results_map)} test cases trong file kết quả cũ. Chế độ: Tự động cộng dồn/cập nhật.")
            except Exception as e:
                print(f"⚠️ Không thể đọc file kết quả cũ ({e}). Sẽ tạo mới.")

        results_map = dict(existing_results_map)

        for idx, tc in enumerate(test_cases, 1):
            tc_id = tc["test_case_id"]
            query = tc["patient_query"]
            gt_answer = tc["ground_truth_answer"]
            gt_chunks = set(tc["ground_truth_chunk_ids"])
            retrieval_type = tc.get("retrieval_type", "EQUIVALENT")

            print(f"\n[{idx}/{len(test_cases)}] Đang kiểm thử: {tc_id} - {tc.get('category', '')}")
            print(f"  Query: \"{query[:70]}...\"")

            # 1. Truy xuất thông tin (Retriever mới: Hybrid RRF + Reranker)
            retrieved_chunks = self.retriever.retrieve(query=query, top_k=3, use_reranker=True)
            retrieved_ids = [c["chunk_id"] for c in retrieved_chunks]
            print(f"  Retrieved Chunks: {retrieved_ids}")
            print(f"  Ground Truth:     {list(gt_chunks)}")

            # 2. Đo IR Metrics nội bộ (Context Recall & Precision)
            hits = [cid for cid in retrieved_ids if cid in gt_chunks]
            
            # Context Recall (Sufficiency / Strict)
            if retrieval_type == "EQUIVALENT":
                c_recall = 1.0 if len(hits) >= 1 else 0.0
            else:
                c_recall = len(hits) / len(gt_chunks) if gt_chunks else 0.0

            # Context Precision: Vị trí của các chunk đúng ở top k
            prec_scores = []
            for rank, cid in enumerate(retrieved_ids, 1):
                if cid in gt_chunks:
                    prec_scores.append(len([c for c in retrieved_ids[:rank] if c in gt_chunks]) / rank)
            c_precision = np.mean(prec_scores) if prec_scores else 0.0

            # Ghép context
            context_text = "\n\n".join(
                [f"[Tài liệu {i+1}]: {c['section_title']}\n{c['content']}" for i, c in enumerate(retrieved_chunks)]
            )

            # 3. Sinh câu trả lời từ RAG
            generated_answer = self._generate_answer(query, context_text)
            print(f"\n  [AI Response]:\n  {generated_answer.strip()}\n")

            # 4. Thẩm định Faithfulness bằng Judge LLM
            faith_prompt = FAITHFULNESS_PROMPT_VN.format(
                context=context_text,
                question=query,
                answer=generated_answer,
            )
            faith_res = self._call_judge_llm(faith_prompt)
            faith_score = float(faith_res.get("score", 0.0))

            # 5. Thẩm định Answer Relevance bằng Judge LLM
            rel_prompt = ANSWER_RELEVANCE_PROMPT_VN.format(
                question=query,
                ground_truth=gt_answer,
                answer=generated_answer,
            )
            rel_res = self._call_judge_llm(rel_prompt)
            rel_score = float(rel_res.get("score", 0.0))

            print(f"  -> Context Recall:    {c_recall:.2f}")
            print(f"  -> Context Precision: {c_precision:.2f}")
            print(f"  -> Faithfulness:      {faith_score:.2f} ({faith_res.get('reason', '')})")
            print(f"  -> Answer Relevance:  {rel_score:.2f} ({rel_res.get('reason', '')})")

            # Giải thích tường minh cho cả 4 chỉ số:
            recall_reason = f"Tìm thấy {len(hits)}/{len(gt_chunks)} chunk chuẩn ({list(hits)})" if gt_chunks else "Không có ground truth"
            precision_reason = f"Thứ hạng các chunk đúng trong Top {len(retrieved_ids)}: {[i for i, cid in enumerate(retrieved_ids, 1) if cid in gt_chunks]}"

            current_case_result = {
                "test_case_id": tc_id,
                "query": query,
                "ground_truth_chunks": list(gt_chunks),
                "retrieved_chunk_ids": retrieved_ids,
                "generated_answer": generated_answer,
                "metrics": {
                    "context_recall": c_recall,
                    "context_precision": c_precision,
                    "faithfulness": faith_score,
                    "answer_relevance": rel_score
                },
                "judge_trace": {
                    "context_recall": {
                        "score": c_recall,
                        "reason": recall_reason
                    },
                    "context_precision": {
                        "score": c_precision,
                        "reason": precision_reason
                    },
                    "faithfulness": {
                        "score": faith_score,
                        "reason": faith_res.get("reason", "")
                    },
                    "answer_relevance": {
                        "score": rel_score,
                        "reason": rel_res.get("reason", "")
                    }
                }
            }

            # Cập nhật kết quả vào từ điển (cộng dồn hoặc ghi đè TC này nếu đã chạy trước đó)
            results_map[tc_id] = current_case_result

            # Danh sách tất cả các cases đã tích luỹ tới hiện tại
            all_saved_details = list(results_map.values())
            recalls = [d["metrics"]["context_recall"] for d in all_saved_details]
            precisions = [d["metrics"]["context_precision"] for d in all_saved_details]
            faiths = [d["metrics"]["faithfulness"] for d in all_saved_details]
            relevances = [d["metrics"]["answer_relevance"] for d in all_saved_details]

            # Lưu ngay lập tức sau MỖI TEST CASE để không bao giờ bị mất dữ liệu
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({
                    "summary": {
                        "total_cases_processed": len(all_saved_details),
                        "mean_context_recall": round(float(np.mean(recalls)), 4) if recalls else 0.0,
                        "mean_context_precision": round(float(np.mean(precisions)), 4) if precisions else 0.0,
                        "mean_faithfulness": round(float(np.mean(faiths)), 4) if faiths else 0.0,
                        "mean_answer_relevance": round(float(np.mean(relevances)), 4) if relevances else 0.0,
                    },
                    "details": all_saved_details
                }, f, ensure_ascii=False, indent=2)

            time.sleep(2)  # Nghỉ 2 giây giữa các request để OpenRouter hạ nhiệt in-flight budget

        # ==============================================================================
        # TỔNG HỢP BÁO CÁO KẾT QUẢ
        # ==============================================================================
        all_final = list(results_map.values())
        print("\n" + "=" * 80)
        print("🏆 BÁO CÁO TỔNG HỢP CHỈ SỐ RAGAS LÂM SÀNG (VIETNAMESE CLINICAL BENCHMARK)")
        print("=" * 80)
        print(f"Tổng số Test Cases đã lưu trong báo cáo: {len(all_final)}")
        if all_final:
            recalls_f = [d["metrics"]["context_recall"] for d in all_final]
            precisions_f = [d["metrics"]["context_precision"] for d in all_final]
            faiths_f = [d["metrics"]["faithfulness"] for d in all_final]
            relevances_f = [d["metrics"]["answer_relevance"] for d in all_final]
            print(f"1. Context Recall (Độ bao phủ tri thức):       {np.mean(recalls_f)*100:.1f}%")
            print(f"2. Context Precision (Độ chính xác thứ hạng):   {np.mean(precisions_f)*100:.1f}%")
            print(f"3. Faithfulness (Tính trung thực / Không ảo giác): {np.mean(faiths_f)*100:.1f}%")
            print(f"4. Answer Relevance (Độ liên quan trực diện):  {np.mean(relevances_f)*100:.1f}%")
        print("=" * 80)
        print(f"Toàn bộ kết quả chi tiết đã được cập nhật liên tục tại: {output_file}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vietnamese Clinical RAGAS Benchmark")
    parser.add_argument("--limit", type=int, default=2, help="Số lượng câu cần test (mặc định: 2)")
    parser.add_argument("--ids", type=str, default="", help="Mã Test Case cụ thể, ví dụ: TC01,TC03")
    args = parser.parse_args()

    evaluator = VietnameseRagasEvaluator()

    if args.ids:
        target_ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
            all_cases = json.load(f)
        filtered = [c for c in all_cases if c["test_case_id"] in target_ids]
        print(f"🎯 Đang kiểm thử {len(filtered)} case theo ID chỉ định: {target_ids}")
        evaluator.evaluate_testset(test_cases_list=filtered)
    else:
        print(f"🎯 Đang kiểm thử {args.limit} câu hỏi đầu tiên...")
        evaluator.evaluate_testset(limit=args.limit)
