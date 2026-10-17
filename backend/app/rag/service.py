import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
from google import genai
from backend.app.core.config import settings
from backend.app.rag.retriever import PgVectorRetriever
from backend.app.rag.prompts import RAG_SYSTEM_PROMPT, PROMPT_TEMPLATE
from backend.app.clinical_agents.triage_agent import TriageAgent

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class AftercareRAGService:
    """Service điều phối toàn bộ luồng RAG và Triage y khoa."""

    def __init__(self):
        self.retriever = PgVectorRetriever()
        self.triage = TriageAgent()

        # OpenRouter Client
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openrouter_client = (
            OpenAI(
                base_url=settings.OPENROUTER_BASE_URL, api_key=self.openrouter_api_key
            )
            if self.openrouter_api_key
            else None
        )

        # Gemini Client (Dự phòng)
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_client = (
            genai.Client(api_key=self.gemini_api_key) if self.gemini_api_key else None
        )

    def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        profiles_dir = BASE_DIR / "Data" / "patient_profiles"
        for p_file in profiles_dir.glob("*.json"):
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("patient_info", {}).get("patient_id") == patient_id:
                    return data
        raise ValueError(f"Không tìm thấy hồ sơ cho bệnh nhân có mã: {patient_id}")

    def process_chat(
        self, patient_id: str, message: str, model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        profile = self.get_patient_profile(patient_id)

        # 1. Đánh giá Triage an toàn y tế (Rule-based state machine)
        safety_status = self.triage.evaluate_risk(message, profile)

        p_info = profile["patient_info"]
        c_status = profile["clinical_status"]
        meds = profile["current_medications"]
        plan = profile["action_plan_rules"]
        follow = profile["follow_up"]

        # 1. HARD RULE ĐIỀU TRỊ CẤP CỨU: Phản xạ bằng CODE thuần túy, tuyệt đối KHÔNG đưa vào LLM
        if safety_status == "RED_ZONE":
            action_text = (
                f"🚨 CẢNH BÁO CỜ ĐỎ CẤP CỨU: Bác/Bạn {p_info['full_name']} đang có dấu hiệu NGUY KỊCH!\n\n"
                f"1. DÙNG NGAY THUỐC CẮT CƠN: Sử dụng ngay {meds.get('reliever_med', 'Thuốc cắt cơn')} theo đúng kế hoạch hành động: {plan['red_zone']}\n"
                f"2. TƯ THẾ AN TOÀN: Ngồi thẳng lưng, hơi cúi người ra phía trước, thở chúm môi chậm rãi. TUYỆT ĐỐI KHÔNG NẰM NGỬA!\n"
                f"3. CẤP CỨU KHẨN CẤP: Nhờ người thân gọi ngay Cấp cứu 115 hoặc di chuyển khẩn cấp tới {follow.get('hospital', 'cơ sở y tế gần nhất')}!"
            )
            return {
                "response": action_text,
                "safety_status": "RED_ZONE",
                "citations": [],
            }

        # 2. RULE CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Phản xạ bằng CODE thuần túy theo Kế hoạch hành động cá nhân
        if safety_status == "YELLOW_ZONE":
            action_text = (
                f"⚠️ CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Bác/Bạn {p_info['full_name']} đang có dấu hiệu hen bùng phát hoặc kiểm soát kém.\n\n"
                f"1. DÙNG THUỐC CẮT CƠN: Dùng ngay {meds.get('reliever_med', 'Thuốc cắt cơn')} theo đúng chỉ định Vùng Vàng: {plan['yellow_zone']}\n"
                f"2. NGHỈ NGƠI TẠI CHỖ: Tránh xa môi trường khói bụi, máy lạnh hoặc tác nhân dị nguyên.\n"
                f"3. THEO DÕI ĐÁNH GIÁ LẠI: Sau 20-30 phút nếu cơn khó thở không giảm hoặc xuất hiện dấu hiệu nguy cấp, cần liên hệ cơ sở y tế ({follow.get('hospital', 'bệnh viện theo dõi')}) ngay."
            )
            return {
                "response": action_text,
                "safety_status": "YELLOW_ZONE",
                "citations": [],
            }

        # 2. Truy vấn tài liệu y khoa từ PgVector (Top 3)
        retrieved_chunks = self.retriever.retrieve(query=message, top_k=3)
        rag_context = ""
        citations = []
        for idx, c in enumerate(retrieved_chunks, 1):
            rag_context += f"\n[Tài liệu {idx}]: {c['section_title']} (Trích dẫn: {c['citation']})\n{c['content']}\n"
            # Tạo URL xem trực tiếp đúng trang PDF (ví dụ: /static/pdf/byt_1851.pdf#page=12)
            pdf_url = (
                f"/api/v1/documents/view/{c['document_tag']}#page={c['pdf_page']}"
                if c.get("pdf_page")
                else None
            )
            citations.append(
                {
                    "chunk_id": c["chunk_id"],
                    "section_title": c["section_title"],
                    "citation": c["citation"],
                    "safety_tier": c["safety_tier"],
                    "document_tag": c.get("document_tag"),
                    "document_name": c.get("document_name"),
                    "pdf_page": c.get("pdf_page"),
                    "pdf_url": pdf_url,
                    "snippet": c.get("content", ""),
                    "similarity_score": c["similarity_score"],
                }
            )

        # 3. Tạo prompt chuẩn lâm sàng (Zero-Hallucination, Patient-aware, Grounding BYT & GINA)
        prompt = PROMPT_TEMPLATE.format(
            system_prompt=RAG_SYSTEM_PROMPT,
            full_name=p_info["full_name"],
            age=p_info["age"],
            gender=p_info["gender"],
            discharge_date=p_info.get("discharge_date", "Chưa rõ"),
            diagnosis=c_status["diagnosis"],
            known_triggers=", ".join(c_status.get("known_triggers", []))
            if c_status.get("known_triggers")
            else "Không ghi nhận",
            controller_med=meds.get(
                "controller_med", "Không dùng thuốc duy trì hàng ngày"
            ),
            reliever_med=meds.get("reliever_med", "Thuốc cắt cơn theo đơn"),
            hospital=follow.get("hospital", "Cơ sở y tế điều trị"),
            next_appointment=follow.get("next_appointment", "Theo lịch hẹn của bác sĩ"),
            rag_context=rag_context
            if rag_context.strip()
            else "Không tìm thấy đoạn tài liệu phù hợp trong cơ sở tri thức.",
            user_query=message,
        )

        response_text = self._call_llm(prompt, model_override=model_override)
        return {
            "response": response_text,
            "safety_status": "NORMAL",
            "citations": citations,
        }

    def _call_llm(self, prompt: str, model_override: str = None) -> str:
        # Nếu model_override là gemini trực tiếp hoặc google/gemini
        if model_override and (
            "gemini" in model_override.lower()
            and not model_override.startswith("openrouter/")
        ):
            if self.gemini_client:
                try:
                    res = self.gemini_client.models.generate_content(
                        model=model_override, contents=prompt
                    )
                    return res.text
                except Exception as e:
                    return f"Lỗi xử lý phản hồi từ Gemini ({model_override}): {str(e)}"

        target_model = model_override or settings.OPENROUTER_MODEL

        # 1. Ưu tiên gọi qua OpenRouter nếu có OPENROUTER_API_KEY
        if self.openrouter_client:
            try:
                chat_completion = self.openrouter_client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=settings.OPENROUTER_MAX_TOKENS,
                    temperature=0.2,
                )
                return chat_completion.choices[0].message.content or ""
            except Exception as e:
                # Nếu OpenRouter gặp lỗi và có Gemini thì thử fallback
                if self.gemini_client:
                    try:
                        res = self.gemini_client.models.generate_content(
                            model=settings.GEMINI_MODEL, contents=prompt
                        )
                        return res.text
                    except Exception:
                        pass
                return f"Lỗi xử lý phản hồi từ OpenRouter ({target_model}): {str(e)}"

        # 2. Dự phòng gọi qua Gemini SDK trực tiếp
        if self.gemini_client:
            try:
                res = self.gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL, contents=prompt
                )
                return res.text
            except Exception as e:
                return f"Lỗi xử lý phản hồi từ mô hình Gemini: {str(e)}"

        return "Lỗi: Chưa cấu hình OPENROUTER_API_KEY (hoặc GEMINI_API_KEY) trong file .env."
