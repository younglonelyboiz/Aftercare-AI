import os
import json
import time
from typing import TypedDict, List
import google.generativeai as genai

class LLMExtractedMetadata(TypedDict):
    topic_category: str
    target_audience: str
    safety_classification: str
    extracted_keywords: List[str]

class GeminiRAGService:
    def __init__(self, api_key: str = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("Không tìm thấy GEMINI_API_KEY trong file .env!")
        genai.configure(api_key=key)
        self.llm_model = genai.GenerativeModel('models/gemini-3.5-flash-lite')
        
    def extract_metadata(self, content: str) -> dict:
        prompt = (
            "Bạn là một chuyên gia phân loại dữ liệu y khoa. Hãy đọc đoạn văn bản sau và trả về JSON chuẩn xác.\n\n"
            "Hướng dẫn gán nhãn:\n"
            "- topic_category: BẮT BUỘC chọn MỘT từ đúng nhất trong: [medication, action_plan, emergency_signs, lifestyle, diagnosis, pathophysiology, general_info]\n"
            "- target_audience: BẮT BUỘC chọn MỘT từ đúng nhất trong: [patient_caregiver, clinician, general_public]\n"
            "- safety_classification: BẮT BUỘC chọn MỘT từ đúng nhất trong: [EDUCATIONAL_SAFE, YELLOW_FLAG, RED_FLAG_THRESHOLD]\n"
            "- extracted_keywords: Tự do trích xuất 3 đến 5 từ khóa/thuật ngữ y khoa quan trọng nhất xuất hiện trong văn bản.\n\n"
            f"Văn bản cần phân loại:\n{content}"
        )
        try:
            response = self.llm_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=LLMExtractedMetadata,
                    temperature=0.1,
                ),
            )
            time.sleep(8)
            return json.loads(response.text)
        except Exception as e:
            print(f"Lỗi khi lấy metadata: {e}")
            return {"topic_category": "general_info", "target_audience": "patient_caregiver", "safety_classification": "EDUCATIONAL_SAFE", "extracted_keywords": []}

    def generate_embedding(self, content: str) -> List[float]:
        try:
            result = genai.embed_content(
                model="models/gemini-embedding-2",
                content=content,
                task_type="retrieval_document",
                title="Knowledge Base Chunk"
            )
            time.sleep(1)
            return result['embedding']
        except Exception as e:
            print(f"Lỗi khi tạo vector: {e}")
            return []