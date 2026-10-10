"""
Configuration module for Aftercare-AI.
Quản lý tập trung các đường dẫn thư mục, khóa API và cấu hình mô hình AI.
"""

import os
from pathlib import Path

# Đường dẫn gốc dự án (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Thư mục dữ liệu và tài liệu
DATA_DIR = BASE_DIR / "Data"
DOCS_DIR = BASE_DIR / "docs"

# Tìm file PDF hướng dẫn điều trị Hen phế quản trong thư mục Data
def get_default_pdf_path() -> Path:
    pdf_files = list(DATA_DIR.glob("*.pdf"))
    if pdf_files:
        return pdf_files[0]
    return DATA_DIR / "Huong-dan-chan-doan-va-dieu-tri-Hen-phe-quan.pdf"

DEFAULT_PDF_PATH = get_default_pdf_path()
DEFAULT_MD_PATH = DATA_DIR / "hen_phe_quan.md"
DEFAULT_RAW_JSON_PATH = DATA_DIR / "rag_knowledge_base_asthma.json"
DEFAULT_COMPACT_JSON_PATH = DATA_DIR / "rag_knowledge.json"

# Cấu hình Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_METADATA_MODEL = os.getenv("LLM_METADATA_MODEL", "models/gemini-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-2")

# Cấu hình phân đoạn RAG
CHUNK_MIN_LENGTH = 20
DOCUMENT_REFERENCE = "BYT-QĐ1851"
SOURCE_AUTHORITY = "Bộ Y tế Việt Nam"
CLINICAL_DOMAIN = "asthma_management"

