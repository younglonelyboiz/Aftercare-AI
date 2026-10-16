"""
RAG Knowledge Base Pipeline Orchestrator.
Điều phối toàn bộ quy trình: Trích xuất PDF -> Làm sạch Markdown -> Phân đoạn ngữ nghĩa -> Gán nhãn LLM & Embedding -> Chuẩn hóa JSON.
"""

import uuid
import json
from pathlib import Path
from typing import Union, List, Dict, Any, Optional

from .cleaner import clean_rag_markdown
from .converter import extract_and_clean_pdf
from .chunker import split_markdown_by_headers
from .embedder import GeminiRAGService
from .formatter import compact_vector_in_existing_json, compact_vector_json_string

# Cập nhật đường dẫn cứng nếu không dùng file config riêng
DOCUMENT_REFERENCE = "BYT-QĐ1851"
SOURCE_AUTHORITY = "Bộ Y tế Việt Nam"
CLINICAL_DOMAIN = "asthma_management"

class RAGPipeline:
    def __init__(self, api_key: Optional[str] = None):
        self.rag_service = GeminiRAGService(api_key=api_key)

    def step1_convert_pdf_to_md(self, pdf_path: str, output_md_path: str) -> Path:
        extract_and_clean_pdf(pdf_path, output_md_path)
        return Path(output_md_path)

    def step2_process_markdown_to_json(self, input_md_path: str, output_json_path: str, compact_output: bool = True) -> Path:
        md_file = Path(input_md_path)
        out_file = Path(output_json_path)

        print(f"[Step 2] Đang đọc nội dung từ: {md_file}...")
        raw_text = md_file.read_text(encoding="utf-8")
        clean_text = clean_rag_markdown(raw_text)

        chunks = split_markdown_by_headers(clean_text)
        dataset: List[Dict[str, Any]] = []
        
        for idx, item in enumerate(chunks):
            content = item["content"]
            section_title = item["section_title"]
            citation_tag = f"[{DOCUMENT_REFERENCE}: {section_title}]"

            print(f"[Step 2] Xử lý đoạn {idx + 1}/{len(chunks)}")
            llm_meta = self.rag_service.extract_metadata(content)
            embedding_vec = self.rag_service.generate_embedding(content)

            chunk_record = {
                "chunk_id": f"CHK-ASTHMA-{str(uuid.uuid4())[:8].upper()}",
                "document_reference": DOCUMENT_REFERENCE,
                "content": content,
                "embedding_vector": embedding_vec,
                "metadata": {
                    "source_authority": SOURCE_AUTHORITY,
                    "clinical_domain": CLINICAL_DOMAIN,
                    "topic_category": llm_meta.get("topic_category", "unknown"),
                    "target_audience": llm_meta.get("target_audience", "patient_caregiver"),
                    "safety_classification": llm_meta.get("safety_classification", "EDUCATIONAL_SAFE"),
                    "citation_tag": citation_tag
                }
            }
            dataset.append(chunk_record)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        if compact_output:
            out_file.write_text(compact_vector_json_string(dataset), encoding="utf-8")
        else:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)

        return out_file

    def step3_compact_json_vectors(self, input_json_path: str, output_json_path: str) -> Path:
        compact_vector_in_existing_json(input_json_path, output_json_path)
        return Path(output_json_path)

    def run_all(self, pdf_path: str, md_path: str, raw_json_path: str, final_json_path: str):
        print("=== BẮT ĐẦU CHẠY TOÀN BỘ RAG KNOWLEDGE PIPELINE ===")
        self.step1_convert_pdf_to_md(pdf_path, md_path)
        self.step2_process_markdown_to_json(md_path, raw_json_path, compact_output=False)
        self.step3_compact_json_vectors(raw_json_path, final_json_path)
        print("=== HOÀN TẤT TOÀN BỘ PIPELINE THÀNH CÔNG! ===")