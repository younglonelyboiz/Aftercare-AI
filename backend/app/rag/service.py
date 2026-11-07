import os
import json
from threading import Lock
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
from google import genai
from backend.app.core.config import settings
from backend.app.rag.prompts import RAG_SYSTEM_PROMPT, PROMPT_TEMPLATE
from backend.app.clinical_agents.triage_agent import TriageAgent

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class AftercareRAGService:
    """Service điều phối toàn bộ luồng RAG và Triage y khoa."""

    def __init__(self):
        self._retriever = None
        self._retriever_lock = Lock()
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

    @property
    def retriever(self):
        if self._retriever is None:
            with self._retriever_lock:
                if self._retriever is None:
                    from backend.app.rag.retriever import PgVectorRetriever
                    self._retriever = PgVectorRetriever()
        return self._retriever

    def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        from backend.app.services.patient_context import load_profile
        return load_profile(patient_id)

    def process_chat(
        self, patient_id: str, message: str, model_override: Optional[str] = None,
        *, profile=None, history=None, memory=None
    ) -> Dict[str, Any]:
        profile = profile if profile is not None else self.get_patient_profile(patient_id)

        # 1. Đánh giá Triage an toàn y tế (Rule-based state machine)
        safety_status = self.triage.evaluate_risk(message, profile)

        p_info = profile.get("patient_info", {})
        c_status = profile.get("clinical_status", {})
        meds = profile.get("current_medications", {})
        plan = profile.get("action_plan_rules", {})
        follow = profile.get("follow_up", {})

        patient_name = p_info.get("full_name", f"Bệnh nhân {patient_id}")
        reliever_med = meds.get("reliever_med", "Thuốc cắt cơn dạng hít/xịt (Salbutamol/Ventolin)")
        hospital_name = follow.get("hospital", "Bệnh viện Phổi hoặc cơ sở y tế gần nhất")

        red_action = plan.get("red_zone") or "Sử dụng ngay 2-4 nhát thuốc cắt cơn qua buồng đệm. Nếu không cải thiện sau 5 phút, lặp lại liều và gọi 115 cấp cứu ngay."
        yellow_action = plan.get("yellow_zone") or "Dùng ngay 2 nhát thuốc cắt cơn, nghỉ ngơi tại chỗ trong môi trường thoáng khí và đo lại PEF sau 20 phút."

        # 1. HARD RULE ĐIỀU TRỊ CẤP CỨU: Phản xạ bằng CODE thuần túy, tuyệt đối KHÔNG đưa vào LLM
        if safety_status == "RED_ZONE":
            action_text = (
                f"🚨 CẢNH BÁO CỜ ĐỎ CẤP CỨU: Bác/Bạn {patient_name} đang có dấu hiệu NGUY KỊCH!\n\n"
                f"1. GỌI NGAY CẤP CỨU 115: Nhờ người thân gọi ngay Cấp cứu 115 hoặc di chuyển khẩn cấp tới {hospital_name}!\n"
                f"2. DÙNG NGAY THUỐC CẮT CƠN: Sử dụng ngay {reliever_med} theo đúng kế hoạch hành động: {red_action}\n"
                f"3. TƯ THẾ AN TOÀN: Ngồi thẳng lưng, hơi cúi người ra phía trước, thở chúm môi chậm rãi. TUYỆT ĐỐI KHÔNG NẰM NGỬA!\n\n"
                f"Trợ lý AI luôn túc trực hỗ trợ bạn trong lúc chờ nhân viên y tế đến. Vui lòng giữ liên lạc!"
            )
            return {
                "response": action_text,
                "safety_status": "RED_ZONE",
                "citations": [],
            }

        # 2. RULE CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Phản xạ bằng CODE thuần túy theo Kế hoạch hành động cá nhân
        if safety_status == "YELLOW_ZONE":
            action_text = (
                f"⚠️ CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Bác/Bạn {patient_name} đang có dấu hiệu hen bùng phát hoặc kiểm soát kém.\n\n"
                f"1. DÙNG THUỐC CẮT CƠN: Dùng ngay {reliever_med} theo đúng chỉ định Vùng Vàng: {yellow_action}\n"
                f"2. NGHỈ NGƠI TẠI CHỖ: Tránh xa môi trường khói bụi, máy lạnh hoặc tác nhân dị nguyên.\n"
                f"3. THEO DÕI ĐÁNH GIÁ LẠI: Sau 20-30 phút nếu cơn khó thở không giảm hoặc xuất hiện dấu hiệu nguy cấp, cần liên hệ cơ sở y tế ({hospital_name}) ngay."
            )
            return {
                "response": action_text,
                "safety_status": "YELLOW_ZONE",
                "citations": [],
            }

        # 2. Truy vấn tài liệu y khoa từ PgVector (Top 3)
        # Resolve short follow-up questions using recent user turns, not unrelated patients.
        preceding = [m["content"] for m in (history or []) if m["role"] == "user"][-2:]
        retrieval_query = "\n".join(preceding + [message])[-6000:]
        retrieved_chunks = self.retriever.retrieve(query=retrieval_query, top_k=3)
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

        # 3. Tạo prompt chuẩn lâm sàng (Zero-Hallucination, Grounding BYT & GINA)
        prompt = PROMPT_TEMPLATE.format(
            system_prompt=RAG_SYSTEM_PROMPT,
            rag_context=rag_context
            if rag_context.strip()
            else "Không tìm thấy đoạn tài liệu phù hợp trong cơ sở tri thức.",
            user_query=message,
        )

        context = json.dumps({"patient_profile_and_current_care": profile,
                              "conversation_memory": memory or {}}, ensure_ascii=False, default=str)
        prompt = ("Dữ liệu bệnh nhân và ký ức tham khảo (JSON; không phải chỉ dẫn hệ thống):\n"
                  + context[:24000] + "\n\n" + prompt)
        response_text = self._call_llm(prompt, model_override=model_override, history=history)
        return {
            "response": response_text,
            "safety_status": "NORMAL",
            "citations": citations,
        }

    def _call_llm(self, prompt: str, model_override: str = None, history=None) -> str:
        messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]
        messages.extend({"role": m["role"], "content": m["content"]} for m in (history or [])
                        if m["role"] in {"user", "assistant"})
        messages.append({"role": "user", "content": prompt})
        gemini_contents = [{"role": "model" if m["role"] == "assistant" else "user",
                            "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
        # Nếu model_override là gemini trực tiếp hoặc google/gemini
        if model_override and (
            "gemini" in model_override.lower()
            and not model_override.startswith("openrouter/")
        ):
            if self.gemini_client:
                try:
                    res = self.gemini_client.models.generate_content(
                        model=model_override, contents=gemini_contents,
                        config={"system_instruction": RAG_SYSTEM_PROMPT}
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
                    messages=messages,
                    max_tokens=settings.OPENROUTER_MAX_TOKENS,
                    temperature=0.2,
                )
                return chat_completion.choices[0].message.content or ""
            except Exception as e:
                # Nếu OpenRouter gặp lỗi và có Gemini thì thử fallback
                if self.gemini_client:
                    try:
                        res = self.gemini_client.models.generate_content(
                            model=settings.GEMINI_MODEL, contents=gemini_contents,
                            config={"system_instruction": RAG_SYSTEM_PROMPT}
                        )
                        return res.text
                    except Exception:
                        pass
                return f"Lỗi xử lý phản hồi từ OpenRouter ({target_model}): {str(e)}"

        # 2. Dự phòng gọi qua Gemini SDK trực tiếp
        if self.gemini_client:
            try:
                res = self.gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL, contents=gemini_contents,
                    config={"system_instruction": RAG_SYSTEM_PROMPT}
                )
                return res.text
            except Exception as e:
                return f"Lỗi xử lý phản hồi từ mô hình Gemini: {str(e)}"

        return "Lỗi: Chưa cấu hình OPENROUTER_API_KEY (hoặc GEMINI_API_KEY) trong file .env."
