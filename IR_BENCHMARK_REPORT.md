# BÁO CÁO KẾT QUẢ THỰC NGHIỆM IR BENCHMARK

- **Tập dữ liệu:** Golden Dataset (20 Test Cases chuẩn hóa)
  - Kho 1: 5 Test Cases (Cảnh báo Cờ đỏ / Cấp cứu)
  - Kho 2: 15 Test Cases (Chăm sóc / Hồi phục / Theo dõi)
- **Tài nguyên tri thức:** 192 Chunks y khoa (Quyết định 1851/QĐ-BYT & GINA 2023)
- **Embedding Model:** `BAAI/bge-m3` (1024-dim, Normalized)
- **Reranker Model:** `BAAI/bge-reranker-base` (Cross-Encoder)

---

## Bảng Tổng Hợp Số Liệu So Sánh 4 Cấu Hình

| Chỉ số (Metric) | 1. Baseline (Dense Toàn Kho) | 2. Phân Hệ (Dense Router) | 3. Phân Hệ (Hybrid RRF) | 4. Phân Hệ + Rerank 🏆 |
| :--- | :---: | :---: | :---: | :---: |
| **Hit Rate@1** | 35.0% | 45.0% | 50.0% | **60.0%** |
| **Hit Rate@3** | 55.0% | 55.0% | 75.0% | **80.0%** |
| **Hit Rate@5** | 60.0% | 60.0% | **85.0%** | 80.0% |
| | | | | |
| **Sufficiency Recall@1** | 35.0% | 45.0% | 50.0% | **60.0%** |
| **Sufficiency Recall@3** | 55.0% | 55.0% | 75.0% | **80.0%** |
| **Sufficiency Recall@5** | 60.0% | 60.0% | **85.0%** | 80.0% |
| **Sufficiency Recall@10** | 85.0% | 90.0% | **95.0%** | **95.0%** |
| | | | | |
| **Strict Recall@1** | 17.5% | 22.5% | 30.0% | **37.5%** |
| **Strict Recall@3** | 35.0% | 37.5% | 55.0% | **57.5%** |
| **Strict Recall@5** | 42.5% | 45.0% | **67.5%** | 60.0% |
| **Strict Recall@10** | 65.0% | 75.0% | 80.0% | **82.5%** |
| | | | | |
| **Precision@1** | 35.0% | 45.0% | 50.0% | **60.0%** |
| **Precision@3** | 21.7% | 23.3% | **31.7%** | **31.7%** |
| **Precision@5** | 15.0% | 16.0% | **24.0%** | 20.0% |
| | | | | |
| **MRR@1** | 0.350 | 0.450 | 0.500 | **0.600** |
| **MRR@3** | 0.442 | 0.500 | 0.600 | **0.683** |
| **MRR@5** | 0.452 | 0.510 | 0.620 | **0.683** |
| | | | | |
| **NDCG@1** | 0.350 | 0.450 | 0.500 | **0.600** |
| **NDCG@3** | 0.332 | 0.357 | 0.495 | **0.547** |
| **NDCG@5** | 0.366 | 0.391 | 0.550 | **0.560** |
