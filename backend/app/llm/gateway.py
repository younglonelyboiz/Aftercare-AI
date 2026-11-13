"""
Cổng gọi mô hình ngôn ngữ lớn (LLM Gateway) có kiểm soát — [W07-T1.7].

Trách nhiệm:
1. Kiểm tra `model_override` theo danh sách trắng (whitelist) trong cấu hình máy chủ.
2. Áp dụng giới hạn thời gian chờ (`LLM_TIMEOUT_SECONDS`) và thử lại tối đa 1 lần.
3. Hỗ trợ truyền lịch sử hội thoại ngắn hạn (`history`) kèm `RAG_SYSTEM_PROMPT` riêng vai trò `system`.
4. Thực thi chuỗi dự phòng: OpenRouter -> Google Gemini SDK -> trả về `None` (tuyệt đối
   không trả chuỗi lỗi kỹ thuật cho người bệnh).
5. Đo độ trễ của lời gọi LLM phục vụ kiểm toán.
"""
import inspect
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from openai import OpenAI

from backend.app.core.config import settings
from backend.app.rag.prompts import RAG_SYSTEM_PROMPT

logger = logging.getLogger("LLMGateway")


@dataclass
class LLMCallResult:
    """Kết quả một lần gọi LLM qua Gateway."""

    text: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    latency_ms: int
    succeeded: bool


class LLMGateway:
    """Cổng gọi LLM tập trung với cơ chế dự phòng và danh sách trắng mô hình."""

    def __init__(
        self,
        openrouter_client: Optional[OpenAI] = None,
        gemini_client: Optional[object] = None,
    ):
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openrouter_client = openrouter_client or (
            OpenAI(
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=self.openrouter_api_key,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=1,
            )
            if self.openrouter_api_key
            else None
        )

        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_client = gemini_client or (
            self._build_gemini_client() if self.gemini_api_key else None
        )

    def _build_gemini_client(self):
        try:
            return genai.Client(
                api_key=self.gemini_api_key,
                http_options={"timeout": int(settings.LLM_TIMEOUT_SECONDS * 1000)},
            )
        except Exception:
            return genai.Client(api_key=self.gemini_api_key)

    def resolve_model(self, model_override: Optional[str]) -> Optional[str]:
        """Chỉ chấp nhận `model_override` nằm trong danh sách trắng của cấu hình máy chủ."""
        if not model_override:
            return None
        if model_override in settings.allowed_llm_models:
            return model_override
        logger.warning(
            "Bỏ qua model_override không nằm trong danh sách trắng: %s",
            model_override,
        )
        return None

    def generate(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        temperature: float = 0.2,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMCallResult:
        """Gọi LLM và trả về `LLMCallResult`. Khi mọi nhà cung cấp lỗi, `text=None`."""
        start_time = time.perf_counter()
        resolved_override = self.resolve_model(model_override)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT}
        ]
        messages.extend(
            {"role": m["role"], "content": m["content"]}
            for m in (history or [])
            if isinstance(m, dict) and m.get("role") in {"user", "assistant"}
        )
        messages.append({"role": "user", "content": prompt})

        gemini_contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
            if m["role"] != "system"
        ]

        # 0. Nếu override chỉ định trực tiếp mô hình Gemini qua Google SDK
        if resolved_override and (
            "gemini" in resolved_override.lower()
            and not resolved_override.startswith("openrouter/")
        ):
            text = self._invoke_gemini(resolved_override, gemini_contents, prompt)
            if text:
                return LLMCallResult(
                    text=text,
                    provider="gemini",
                    model=resolved_override,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    succeeded=True,
                )

        target_model = resolved_override or settings.OPENROUTER_MODEL

        # 1. Ưu tiên gọi qua OpenRouter
        if self.openrouter_client:
            text = self._invoke_openrouter(
                target_model, messages, temperature=temperature
            )
            if text:
                return LLMCallResult(
                    text=text,
                    provider="openrouter",
                    model=target_model,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    succeeded=True,
                )

        # 2. Dự phòng gọi qua Google Gemini SDK
        text = self._invoke_gemini(settings.GEMINI_MODEL, gemini_contents, prompt)
        if text:
            return LLMCallResult(
                text=text,
                provider="gemini",
                model=settings.GEMINI_MODEL,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                succeeded=True,
            )

        if not self.openrouter_client and not self.gemini_client:
            logger.error(
                "Chưa cấu hình OPENROUTER_API_KEY hoặc GEMINI_API_KEY trong tệp .env."
            )

        return LLMCallResult(
            text=None,
            provider=None,
            model=None,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
            succeeded=False,
        )

    def _invoke_openrouter(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> Optional[str]:
        if not self.openrouter_client:
            return None
        try:
            chat_completion = self.openrouter_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=settings.OPENROUTER_MAX_TOKENS,
                temperature=temperature,
            )
            text = chat_completion.choices[0].message.content or ""
            if text.strip():
                return text
            logger.error("OpenRouter (%s) trả về nội dung rỗng.", model)
        except Exception:
            logger.exception("Lỗi gọi OpenRouter (%s).", model)
        return None

    def _invoke_gemini(
        self, model: str, gemini_contents: Any, raw_prompt: str
    ) -> Optional[str]:
        if not self.gemini_client:
            return None
        try:
            gen_fn = self.gemini_client.models.generate_content
            try:
                sig = inspect.signature(gen_fn)
                accepts_config = "config" in sig.parameters or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                )
            except (ValueError, TypeError):
                accepts_config = True

            if accepts_config:
                res = gen_fn(
                    model=model,
                    contents=gemini_contents,
                    config={"system_instruction": RAG_SYSTEM_PROMPT},
                )
            else:
                res = gen_fn(model=model, contents=raw_prompt)
            text = getattr(res, "text", None) or ""
            if text.strip():
                return text
            logger.error("Gemini (%s) trả về nội dung rỗng.", model)
        except Exception:
            logger.exception("Lỗi gọi Gemini (%s).", model)
        return None
