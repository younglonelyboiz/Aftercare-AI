import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Aftercare-AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # OpenRouter & Gemini LLM
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MAX_TOKENS: int = int(os.getenv("OPENROUTER_MAX_TOKENS", "1500"))

    # Gemini LLM (Fallback)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", os.getenv("LLM_CLINICAL_MODEL", "gemini-2.5-flash"))

    # Embedding Model (BAAI/bge-m3)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cuda")

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
