# HƯỚNG DẪN CÀI ĐẶT, SEED DATABASE & KHỞI CHẠY HỆ THỐNG
## (Hỗ trợ đầy đủ Linux Ubuntu/Debian & Windows PowerShell / CMD)

Dự án **Aftercare-AI** bao gồm 3 thành phần chính:
1. **Database:** PostgreSQL kèm extension `pgvector` (chạy Docker hoặc cài trực tiếp).
2. **Backend API:** Python FastAPI + PgVector Retriever (BGE-M3 + Reranker) + Triage Agent.
3. **Frontend Web:** React 19 + Vite + Tailwind/CSS.

---

## 1. YÊU CẦU TIỀN ĐỀ (PREREQUISITES)

| Thành phần | Phiên bản tối thiểu khuyến nghị | Ghi chú |
| :--- | :--- | :--- |
| **Python** | `3.10` hoặc `3.11` | Cần thiết lập `python` / `python3` trong PATH |
| **Node.js & npm** | `Node 18+` / `npm 9+` | Dùng để chạy Frontend React Vite |
| **Docker & Docker Compose** | Docker Desktop (Win) / Docker Engine (Linux) | Khuyến nghị dùng để dựng PostgreSQL PgVector nhanh |
| **GPU (Tùy chọn)** | NVIDIA CUDA 11.8+ / 12+ | Giúp embed BGE-M3 cực nhanh (không có vẫn chạy mượt trên CPU) |

---

## 2. THIẾT LẬP FILE CẤU HÌNH (.env)

Tạo file `.env` tại thư mục gốc của dự án (`Aftercare-AI/`):

```bash
# ------------------------------------------------------------------------------
# 1. MÔ HÌNH NGÔN NGỮ (LLM)
# ------------------------------------------------------------------------------
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=openai/gpt-4o
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MAX_TOKENS=1500

GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# ------------------------------------------------------------------------------
# 2. EMBEDDING MODEL (Dense Vector 1024 dims)
# ------------------------------------------------------------------------------
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
EMBEDDING_DEVICE=cuda   # hoặc đặt là 'cpu' nếu máy không có card NVIDIA

# ------------------------------------------------------------------------------
# 3. POSTGRESQL & PGVECTOR DATABASE
# ------------------------------------------------------------------------------
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aftercare_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgrespassword

PGVECTOR_TABLE_NAME=medical_knowledge_chunks
```

---

## 3. KHỞI TẠO CƠ SỞ DỮ LIỆU POSTGRESQL & PGVECTOR

### Cách 1: Sử dụng Docker (Khuyến nghị cho cả Linux & Windows)

Chạy lệnh Docker để dựng nhanh container PostgreSQL có sẵn extension `pgvector`:

#### Trên Linux (Terminal):
```bash
docker run -d \
  --name aftercare-postgres \
  -e POSTGRES_DB=aftercare_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgrespassword \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

#### Trên Windows (PowerShell / CMD):
```powershell
docker run -d `
  --name aftercare-postgres `
  -e POSTGRES_DB=aftercare_db `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgrespassword `
  -p 5432:5432 `
  pgvector/pgvector:pg16
```

---

## 4. CÀI ĐẶT MÔI TRƯỜNG BACKEND & SEED DỮ LIỆU

### Bước 4.1: Tạo môi trường ảo Python

#### 👉 Dành cho Linux:
```bash
# Di chuyển vào thư mục dự án
cd Aftercare-AI

# Tạo virtualenv
python3 -m venv venv
source venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt
```

#### 👉 Dành cho Windows (PowerShell):
```powershell
# Di chuyển vào thư mục dự án
cd Aftercare-AI

# Tạo virtualenv
python -m venv venv
.\venv\Scripts\Activate.ps1

# (Nếu PowerShell chặn script, chạy: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser)

# Cài đặt thư viện phụ thuộc
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Bước 4.2: Chạy SEED Dữ Liệu vào PgVector (192 Chunks Tri Thức Y Khoa)

Hệ thống đã chuẩn bị sẵn file seed nhúng vector đầy đủ metadata: `Data/embedded_rag_chunks_bge_m3.json`. Quá trình seed sẽ tự động:
1. Kích hoạt `CREATE EXTENSION IF NOT EXISTS vector;`
2. Tạo bảng `medical_knowledge_chunks` với chỉ mục `HNSW` Cosine Distance.
3. Nạp toàn bộ 192 chunks kèm nhãn phân kho (`KHO_1_CANH_BAO_CO_DO_CAP_CUU`, `KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI`), trích dẫn và số trang PDF.

#### 👉 Lệnh Seed trên Linux:
```bash
# Đảm bảo virtualenv đang bật
python3 pipeline/ingest_to_pgvector.py
```

#### 👉 Lệnh Seed trên Windows:
```powershell
# Đảm bảo virtualenv đang bật
python pipeline/ingest_to_pgvector.py
```

> **Kết quả thành công sẽ hiển thị:**
> `✓ THÀNH CÔNG! Đã nạp toàn bộ 192 chunks (1024 dims) vào PostgreSQL PgVector!`  
> `✓ Tổng số bản ghi thực tế trong bảng 'medical_knowledge_chunks': 192`

---

### Bước 4.3: Chạy MIGRATION & SEED Dữ Liệu Care Plan, Nhắc Thuốc & Check-in (Asthma Tracker)

Hệ thống cung cấp sẵn bộ script khởi tạo bảng và seed dữ liệu chuẩn GINA cho 3 bệnh nhân mẫu (nhẹ, nặng, kèm GERD) cùng lịch sử 14 ngày:

#### 1. Khởi tạo cấu trúc bảng (Migration):
* **Trên Linux:**
  ```bash
  PYTHONPATH=. python3 backend/app/db/migrate_asthma_tables.py
  ```
* **Trên Windows:**
  ```powershell
  $env:PYTHONPATH="."
  python backend/app/db/migrate_asthma_tables.py
  ```

#### 2. Nạp dữ liệu mẫu (Care Plans, Reminders, 14-day Checkin Logs):
* **Trên Linux:**
  ```bash
  PYTHONPATH=. python3 backend/app/db/seed_asthma_care_plans.py
  ```
* **Trên Windows:**
  ```powershell
  $env:PYTHONPATH="."
  python backend/app/db/seed_asthma_care_plans.py
  ```

> **Kết quả thành công sẽ hiển thị:**
> `✓ Khởi tạo bảng Asthma thành công 100%!`  
> `✓ Seed dữ liệu Care Plans & Checkin cho 3 bệnh nhân Hen phế quản thành công 100%!`

---

## 5. KHỞI CHẠY BACKEND API (FastAPI)

Backend chạy tại cổng mặc định: `http://localhost:8000` (Tài liệu API Swagger tại `http://localhost:8000/docs`).

#### 👉 Khởi chạy trên Linux:
```bash
source venv/bin/activate
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 👉 Khởi chạy trên Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 6. CÀI ĐẶT & KHỞI CHẠY FRONTEND (React + Vite)

Frontend chạy tại cổng mặc định: `http://localhost:5173`.

#### 👉 Khởi chạy trên Linux / Windows:
```bash
# Mở một cửa sổ Terminal / PowerShell mới
cd Aftercare-AI/frontend

# Cài đặt packages
npm install

# Khởi chạy dev server
npm run dev
```

Truy cập trình duyệt tại: **`http://localhost:5173`**

---

## 7. CHẠY KIỂM THỬ BENCHMARK IR TRÊN DATASET CHUẨN

Để chạy kiểm thử so sánh độ chính xác của 4 cấu hình tìm kiếm (Baseline Dense, Phân hệ Router, Hybrid RRF, và Hybrid + Reranker BAAI):

#### 👉 Trên Linux:
```bash
python3 scripts/benchmark_2_stores_configurations.py
```

#### 👉 Trên Windows:
```powershell
python scripts/benchmark_2_stores_configurations.py
```

Báo cáo kết quả chi tiết sẽ được tự động xuất ra file `IR_BENCHMARK_REPORT.md`.

---

## 8. CÁC LỖI THƯỜNG GẶP & CÁCH XỬ LÝ (TROUBLESHOOTING)

1. **Lỗi `ModuleNotFoundError: No module named 'psycopg2'`**:
   - Chạy `pip install psycopg2-binary`.
2. **Lỗi `Connection refused` tới PostgreSQL cổng 5432**:
   - Kiểm tra xem Docker container đã chạy chưa bằng lệnh: `docker ps`. Nếu chưa, chạy `docker start aftercare-postgres`.
3. **Lỗi `CUDA out of memory` khi nạp BGE-M3 trên máy GPU yếu**:
   - Chuyển `EMBEDDING_DEVICE=cpu` trong file `.env`.
4. **Lỗi PowerShell không cho kích hoạt `venv` trên Windows**:
   - Mở PowerShell với quyền Administrator và chạy lệnh:
     ```powershell
     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
     ```
