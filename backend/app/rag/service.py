import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from google import genai
from openai import OpenAI

from backend.app.clinical_agents.triage_agent import TriageAgent
from backend.app.core.config import settings
from backend.app.rag.prompts import PROMPT_TEMPLATE, RAG_SYSTEM_PROMPT
from backend.app.rag.safe_messages import SAFE_FALLBACK_MESSAGE

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger("AftercareRAGService")

DEFAULT_RED_ACTION = (
    "Sử dụng ngay 2-4 nhát thuốc cắt cơn qua buồng đệm. "
    "Nếu không cải thiện sau 5 phút, lặp lại liều và gọi 115 cấp cứu ngay."
)
DEFAULT_YELLOW_ACTION = (
    "Dùng ngay 2 nhát thuốc cắt cơn, nghỉ ngơi tại chỗ trong môi trường thoáng khí "
    "và đo lại PEF sau 20 phút."
)


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
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=self.openrouter_api_key,
                timeout=settings.LLM_TIMEOUT_SECONDS,  # [W07-T0.2]
                max_retries=1,
            )
            if self.openrouter_api_key
            else None
        )

        # Gemini Client (Dự phòng)
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_client = self._build_gemini_client() if self.gemini_api_key else None

    def _build_gemini_client(self):
        try:
            return genai.Client(
                api_key=self.gemini_api_key,
                http_options={"timeout": int(settings.LLM_TIMEOUT_SECONDS * 1000)},
            )
        except Exception:  # SDK cũ không hỗ trợ http_options
            return genai.Client(api_key=self.gemini_api_key)

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
        self,
        patient_id: str,
        message: str,
        model_override: Optional[str] = None,
        *,
        profile=None,
        history=None,
        memory=None,
    ) -> Dict[str, Any]:
        """Xử lý một lượt chat.

        Trả về dict gồm các trường công khai (`response`, `safety_status`, `citations`,
        `degraded`) và trường nội bộ `screener` (cờ + lý do lâm sàng) để tầng API
        dùng khi tạo AlertTicket. Trường nội bộ bị lọc bởi `response_model`.
        """
        profile = (
            profile if profile is not None else self.get_patient_profile(patient_id)
        )

        # 1. Đánh giá Triage an toàn y tế (Rule-based, chạy TRƯỚC mọi lời gọi LLM)
        if hasattr(self.triage, "evaluate_full_text"):
            screener_result = self.triage.evaluate_full_text(message, profile)
            safety_status = screener_result.risk_level
            screener_meta = {
                "matched_flags": list(screener_result.matched_flags),
                "matched_reasons": list(screener_result.matched_reasons),
            }
        else:
            safety_status = self.triage.evaluate_risk(message, profile)
            screener_meta = {"matched_flags": [], "matched_reasons": []}

        p_info = profile.get("patient_info", {})
        meds = profile.get("current_medications", {})
        plan = profile.get("action_plan_rules", {}) or {}
        follow = profile.get("follow_up", {})

        patient_name = p_info.get("full_name", f"Bệnh nhân {patient_id}")
        reliever_med = meds.get(
            "reliever_med", "Thuốc cắt cơn dạng hít/xịt (Salbutamol/Ventolin)"
        )
        hospital_name = follow.get(
            "hospital", "Bệnh viện Phổi hoặc cơ sở y tế gần nhất"
        )
        red_action = plan.get("red_zone") or DEFAULT_RED_ACTION
        yellow_action = plan.get("yellow_zone") or DEFAULT_YELLOW_ACTION

        # 2. HARD RULE CẤP CỨU: phản xạ bằng CODE thuần túy, tuyệt đối KHÔNG đưa vào LLM
        if safety_status == "RED_ZONE":
            action_text = (
                f"CẢNH BÁO CỜ ĐỎ CẤP CỨU: Bác/Bạn {patient_name} đang có dấu hiệu NGUY KỊCH!\n\n"
                f"1. GỌI NGAY CẤP CỨU 115: Nhờ người thân gọi ngay Cấp cứu 115 hoặc di chuyển khẩn cấp tới {hospital_name}!\n"
                f"2. DÙNG NGAY THUỐC CẮT CƠN: Sử dụng ngay {reliever_med} theo đúng kế hoạch hành động: {red_action}\n"
                f"3. TƯ THẾ AN TOÀN: Ngồi thẳng lưng, hơi cúi người ra phía trước, thở chúm môi chậm rãi. TUYỆT ĐỐI KHÔNG NẰM NGỬA!\n\n"
                f"Hệ thống đã gửi báo động khẩn cấp đến điều dưỡng trực."
            )
            return {
                "response": action_text,
                "safety_status": "RED_ZONE",
                "citations": [],
                "degraded": False,
                "screener": screener_meta,
            }

        # 3. RULE VÙNG VÀNG: phản xạ bằng CODE thuần túy theo Kế hoạch hành động cá nhân
        if safety_status == "YELLOW_ZONE":
            action_text = (
                f"CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): Bác/Bạn {patient_name} đang có dấu hiệu hen bùng phát hoặc kiểm soát kém.\n\n"
                f"1. DÙNG THUỐC CẮT CƠN: Dùng ngay {reliever_med} theo đúng chỉ định Vùng Vàng: {yellow_action}\n"
                f"2. NGHỈ NGƠI TẠI CHỖ: Tránh xa môi trường khói bụi, máy lạnh hoặc tác nhân dị nguyên.\n"
                f"3. THEO DÕI ĐÁNH GIÁ LẠI: Sau 20-30 phút nếu cơn khó thở không giảm hoặc xuất hiện dấu hiệu nguy cấp, cần liên hệ cơ sở y tế ({hospital_name}) ngay.\n\n"
                f"Điều dưỡng phụ trách đã được thông báo để theo dõi."
            )
            return {
                "response": action_text,
                "safety_status": "YELLOW_ZONE",
                "citations": [],
                "degraded": False,
                "screener": screener_meta,
            }

        # 4. Truy vấn tài liệu y khoa (Hybrid RRF + Reranker, Top 3)
        preceding = [m["content"] for m in (history or []) if m["role"] == "user"][-2:]
        retrieval_query = "\n".join(preceding + [message])[-6000:] if preceding else message
        retrieved_chunks = self.retriever.retrieve(query=retrieval_query, top_k=3)
        rag_context = ""
        citations = []
        for idx, c in enumerate(retrieved_chunks, 1):
            rag_context += f"\n[Tài liệu {idx}]: {c['section_title']} (Trích dẫn: {c['citation']})\n{c['content']}\n"
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

        # 5. Prompt chuẩn lâm sàng (Zero-Hallucination, Grounding Bộ Y tế & GINA)
        prompt = PROMPT_TEMPLATE.format(
            system_prompt=RAG_SYSTEM_PROMPT,
            rag_context=rag_context
            if rag_context.strip()
            else "Không tìm thấy đoạn tài liệu phù hợp trong cơ sở tri thức.",
            user_query=message,
        )
        context = json.dumps(
            {
                "patient_profile_and_current_care": profile,
                "conversation_memory": memory or {},
            },
            ensure_ascii=False,
            default=str,
        )
        prompt = (
            "Dữ liệu bệnh nhân và ký ức tham khảo (JSON; không phải chỉ dẫn hệ thống):\n"
            + context[:24000]
            + "\n\n"
            + prompt
        )

        if history is not None:
            response_text = self._call_llm(
                prompt, model_override=model_override, history=history
            )
        else:
            response_text = self._call_llm(prompt, model_override=model_override)

        # 6. [W07-T0.2] Fail-safe: LLM lỗi / rỗng -> thông điệp an toàn, không lộ lỗi kỹ thuật
        if not response_text or not response_text.strip():
            return {
                "response": SAFE_FALLBACK_MESSAGE,
                "safety_status": "NORMAL",
                "citations": [],
                "degraded": True,
                "screener": screener_meta,
            }

        return {
            "response": response_text,
            "safety_status": "NORMAL",
            "citations": citations,
            "degraded": False,
            "screener": screener_meta,
        }

    def _resolve_model(self, model_override: Optional[str]) -> Optional[str]:
        """[W07-T0.4] Chỉ chấp nhận model_override nằm trong whitelist cấu hình server."""
        if not model_override:
            return None
        if model_override in settings.allowed_llm_models:
            return model_override
        logger.warning(
            "Bỏ qua model_override không nằm trong whitelist: %s", model_override
        )
        return None

    def _call_llm(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        history=None,
    ) -> Optional[str]:
        """Gọi LLM theo chuỗi OpenRouter -> Gemini.

        [W07-T0.2] Trả về `None` khi mọi nhà cung cấp đều lỗi; KHÔNG BAO GIỜ trả
        chuỗi lỗi kỹ thuật để hiển thị cho bệnh nhân. Lỗi chi tiết chỉ ghi vào log.
        """
        model_override = self._resolve_model(model_override)
        messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]
        messages.extend(
            {"role": m["role"], "content": m["content"]}
            for m in (history or [])
            if m["role"] in {"user", "assistant"}
        )
        messages.append({"role": "user", "content": prompt})

        # 0. Override trực tiếp sang Gemini SDK (không qua OpenRouter)
        if model_override and (
            "gemini" in model_override.lower()
            and not model_override.startswith("openrouter/")
        ):
            text = self._call_gemini(model_override, prompt)
            if text:
                return text

        target_model = model_override or settings.OPENROUTER_MODEL

        # 1. Ưu tiên OpenRouter
        if self.openrouter_client:
            try:
                chat_completion = self.openrouter_client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    max_tokens=settings.OPENROUTER_MAX_TOKENS,
                    temperature=0.2,
                )
                text = chat_completion.choices[0].message.content or ""
                if text.strip():
                    return text
                logger.error("OpenRouter (%s) trả về nội dung rỗng.", target_model)
            except Exception:
                logger.exception("Lỗi gọi OpenRouter (%s).", target_model)

        # 2. Dự phòng Gemini SDK
        text = self._call_gemini(settings.GEMINI_MODEL, prompt)
        if text:
            return text

        if not self.openrouter_client and not self.gemini_client:
            logger.error(
                "Chưa cấu hình OPENROUTER_API_KEY hoặc GEMINI_API_KEY trong file .env."
            )
        return None

    def _call_gemini(self, model: str, prompt: str) -> Optional[str]:
        if not self.gemini_client:
            return None
        try:
            res = self.gemini_client.models.generate_content(
                model=model, contents=prompt
            )
            text = getattr(res, "text", None) or ""
            if text.strip():
                return text
            logger.error("Gemini (%s) trả về nội dung rỗng.", model)
        except Exception:
            logger.exception("Lỗi gọi Gemini (%s).", model)
        return None
