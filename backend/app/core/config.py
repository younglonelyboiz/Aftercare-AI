import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Aftercare-AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEMO_LOGIN_ENABLED: bool = os.getenv("DEMO_LOGIN_ENABLED", "false").lower() == "true"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    SESSION_HOURS: int = int(os.getenv("SESSION_HOURS", "8"))
    CORS_ORIGINS: list[str] = [v.strip() for v in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if v.strip()]

    # OpenRouter & Gemini LLM
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MAX_TOKENS: int = int(os.getenv("OPENROUTER_MAX_TOKENS", "1500"))

    # Gemini LLM (Fallback)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", os.getenv("LLM_CLINICAL_MODEL", "gemini-2.5-flash"))

    # [W07-T0.4] Whitelist model LLM được phép dùng khi có model_override nội bộ.
    # Danh sách phân tách bằng dấu phẩy. Model mặc định (OPENROUTER_MODEL, GEMINI_MODEL) luôn được phép.
    ALLOWED_LLM_MODELS: list = [
        m.strip() for m in os.getenv("ALLOWED_LLM_MODELS", "").split(",") if m.strip()
    ]
    # [W07-T0.2] Timeout (giây) cho mỗi lần gọi LLM bên ngoài.
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    # [W07-T3.1 & T3.2] Ngưỡng điểm tối thiểu của cổng bằng chứng (Evidence Gate threshold tau).
    EVIDENCE_MIN_SCORE: float = float(os.getenv("EVIDENCE_MIN_SCORE", "0.35"))

    @property
    def allowed_llm_models(self) -> set:
        return {self.OPENROUTER_MODEL, self.GEMINI_MODEL, *self.ALLOWED_LLM_MODELS}

    # Embedding Model (BAAI/bge-m3)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cuda")

    # Reranker Model (BAAI/bge-reranker-base)
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    RERANKER_DEVICE: str = os.getenv("RERANKER_DEVICE", "cuda")

    # Database PostgreSQL & PgVector
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aftercare_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgrespassword")
    PGVECTOR_TABLE_NAME: str = os.getenv("PGVECTOR_TABLE_NAME", "medical_knowledge_chunks")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
