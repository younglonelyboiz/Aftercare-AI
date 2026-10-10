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
from ..config import (
    DEFAULT_PDF_PATH,
    DEFAULT_MD_PATH,
    DEFAULT_RAW_JSON_PATH,
    DEFAULT_COMPACT_JSON_PATH,
    DOCUMENT_REFERENCE,
    SOURCE_AUTHORITY,
    CLINICAL_DOMAIN,
)

class RAGPipeline:
    """Pipeline xử lý dữ liệu tri thức phác đồ điều trị cho hệ thống Aftercare-AI."""

    def __init__(self, api_key: Optional[str] = None):
        self.rag_service = GeminiRAGService(api_key=api_key)

    def step1_convert_pdf_to_md(
        self,
        pdf_path: Union[str, Path] = DEFAULT_PDF_PATH,
        output_md_path: Union[str, Path] = DEFAULT_MD_PATH
    ) -> Path:
        """Bước 1: Chuyển đổi PDF sang Markdown và dọn dẹp nội dung rác."""
        extract_and_clean_pdf(pdf_path, output_md_path)
        return Path(output_md_path)

    def step2_process_markdown_to_json(
        self,
        input_md_path: Union[str, Path] = DEFAULT_MD_PATH,
        output_json_path: Union[str, Path] = DEFAULT_RAW_JSON_PATH,
        compact_output: bool = True
    ) -> Path:
        """
        Bước 2: Đọc Markdown -> Cắt chunks ngữ nghĩa -> Tạo metadata & vector -> Lưu JSON.
        """
        md_file = Path(input_md_path)
        out_file = Path(output_json_path)

        if not md_file.exists():
            raise FileNotFoundError(f"Không tìm thấy file Markdown: {md_file}")

        print(f"[Step 2] Đang đọc nội dung từ: {md_file}...")
        raw_text = md_file.read_text(encoding="utf-8")
        clean_text = clean_rag_markdown(raw_text)

        print("[Step 2] Đang phân mảnh ngữ nghĩa theo tiêu đề...")
        chunks = split_markdown_by_headers(clean_text)
        print(f"[Step 2] Đã tách thành {len(chunks)} đoạn ngữ nghĩa. Đang xử lý qua Gemini API...")

        dataset: List[Dict[str, Any]] = []
        for idx, item in enumerate(chunks):
            content = item["content"]
            section_title = item["section_title"]
            citation_tag = f"[{DOCUMENT_REFERENCE}: {section_title}]"

            print(f"[Step 2] Xử lý đoạn {idx + 1}/{len(chunks)}: '{section_title[:40]}...'")
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

        print(f"[Step 2] Thành công! Đã lưu {len(dataset)} bản ghi tri thức vào: {out_file}")
        return out_file

    def step3_compact_json_vectors(
        self,
        input_json_path: Union[str, Path] = DEFAULT_RAW_JSON_PATH,
        output_json_path: Union[str, Path] = DEFAULT_COMPACT_JSON_PATH
    ) -> Path:
        """Bước 3: Nén dòng vector trong file JSON để tối ưu dung lượng và định dạng."""
        compact_vector_in_existing_json(input_json_path, output_json_path)
        return Path(output_json_path)

    def run_all(
        self,
        pdf_path: Union[str, Path] = DEFAULT_PDF_PATH,
        md_path: Union[str, Path] = DEFAULT_MD_PATH,
        raw_json_path: Union[str, Path] = DEFAULT_RAW_JSON_PATH,
        final_json_path: Union[str, Path] = DEFAULT_COMPACT_JSON_PATH
    ):
        """Chạy toàn bộ pipeline từ PDF ban đầu đến file JSON cơ sở tri thức hoàn chỉnh."""
        print("=== BẮT ĐẦU CHẠY TOÀN BỘ RAG KNOWLEDGE PIPELINE ===")
        self.step1_convert_pdf_to_md(pdf_path, md_path)
        self.step2_process_markdown_to_json(md_path, raw_json_path, compact_output=False)
        self.step3_compact_json_vectors(raw_json_path, final_json_path)
        print("=== HOÀN TẤT TOÀN BỘ PIPELINE THÀNH CÔNG! ===")

