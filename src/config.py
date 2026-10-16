"""
Configuration module for Aftercare-AI.
Quản lý tập trung các đường dẫn thư mục, khóa API và cấu hình mô hình AI theo đúng cấu trúc dự án.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Tự động load biến môi trường từ file .env
load_dotenv()

# Đường dẫn gốc dự án (project root)
# Giả định file config.py đặt trong thư mục src/ (tức là src/config.py)
# Nếu đặt ở src/data_pipeline/config.py thì dùng: BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# 1. CẤU TRÚC THƯ MỤC CHÍNH
# ==========================================
DATA_DIR = BASE_DIR / "Data"
SRC_DIR = BASE_DIR / "src"

# Các phân hệ con trong Data/
RAW_DIR = DATA_DIR / "raw"                      # Chứa tài liệu gốc (PDF, MD thô)
PROCESSED_DIR = DATA_DIR / "processed"          # Chứa dữ liệu làm sạch, gán nhãn (JSON)
QDRANT_DB_DIR = DATA_DIR / "qdrant_db"          # Database Vector vật lý
PATIENT_PROFILES_DIR = DATA_DIR / "patient_profiles" # Hồ sơ bệnh án

# ==========================================
# 2. ĐƯỜNG DẪN CÁC FILE CỤ THỂ
# ==========================================
# Tự động tạo thư mục nếu chưa tồn tại
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PDF_PATH = RAW_DIR / "Hướng-dẫn-chẩn-đoán-và-điều-trị-Hen-phế-quản-người-lớn-và-trẻ-_12-tuổi.pdf"
DEFAULT_MD_PATH = RAW_DIR / "hen_phe_quan.md"
DEFAULT_RAW_JSON_PATH = PROCESSED_DIR / "rag_knowledge.json"


# ==========================================
# 3. CẤU HÌNH AI & VECTOR DB
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Sử dụng model mới nhất cho metadata (2.5-flash) và embedding 3072 chiều (001 hoặc text-embedding-004)
LLM_METADATA_MODEL = os.getenv("LLM_METADATA_MODEL", "gemini-3.5-flash_lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-2") 

QDRANT_COLLECTION_NAME = "DATN26_medical_guidelines"

# ==========================================
# 4. CẤU HÌNH PHÂN ĐOẠN RAG & SIÊU DỮ LIỆU
# ==========================================
CHUNK_MIN_LENGTH = 20
DOCUMENT_REFERENCE = "BYT-QĐ1851"
SOURCE_AUTHORITY = "Bộ Y tế Việt Nam"
CLINICAL_DOMAIN = "asthma_management"