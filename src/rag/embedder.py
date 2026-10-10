"""
Embedder & Metadata extractor module using Google Gemini API.
Trích xuất siêu dữ liệu y khoa (phân loại an toàn, chủ đề, đối tượng) và tạo vector nhúng.
"""

import os
import json
from typing import List, Dict, Any, Optional

from ..config import GEMINI_API_KEY, LLM_METADATA_MODEL, EMBEDDING_MODEL

try:
    from pydantic import BaseModel, Field

    class LLMExtractedMetadata(BaseModel):
        """Schema siêu dữ liệu y khoa được chuẩn hóa tự động qua LLM."""
        topic_category: str = Field(description="Phân loại chủ đề, vd: medication, emergency_signs, lifestyle, action_plan, disease_overview")
        target_audience: str = Field(description="Đối tượng người đọc, vd: patient_caregiver, clinician")
        safety_classification: str = Field(description="Phân loại an toàn y tế, vd: EDUCATIONAL_SAFE, RED_FLAG_THRESHOLD, YELLOW_FLAG")
except ImportError:
    class LLMExtractedMetadata:
        """Fallback class khi pydantic chưa được cài đặt."""
        pass

class GeminiRAGService:
    """Service bao đóng các tương tác với Gemini API cho RAG pipeline."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
            except ImportError:
                print("Cảnh báo: Chưa cài đặt thư viện 'google-generativeai'. Cài đặt bằng: pip install google-generativeai")
        self.metadata_model_name = LLM_METADATA_MODEL
        self.embedding_model_name = EMBEDDING_MODEL

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Dùng Gemini để tự động gán nhãn siêu dữ liệu phân loại y tế."""
        if not self.api_key:
            return {
                "topic_category": "unknown",
                "target_audience": "patient_caregiver",
                "safety_classification": "EDUCATIONAL_SAFE"
            }

        prompt = f"Phân loại đoạn văn bản y khoa sau và trả về JSON chuẩn xác:\n\n{content}"
        try:
            model = genai.GenerativeModel(self.metadata_model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=LLMExtractedMetadata,
                    temperature=0.1,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Cảnh báo: Không thể trích xuất metadata bằng LLM ({e}), sử dụng nhãn mặc định.")
            return {
                "topic_category": "unknown",
                "target_audience": "patient_caregiver",
                "safety_classification": "EDUCATIONAL_SAFE"
            }

    def generate_embedding(self, content: str) -> List[float]:
        """Tạo vector nhúng ngữ nghĩa (embedding) cho đoạn tài liệu."""
        if not self.api_key:
            return []

        try:
            result = genai.embed_content(
                model=self.embedding_model_name,
                content=content,
                task_type="retrieval_document",
                title="Knowledge Base Chunk"
            )
            return result.get('embedding', [])
        except Exception as e:
            print(f"Cảnh báo: Lỗi khi tạo vector nhúng ({e}).")
            return []
