# BÁO CÁO TỔNG QUAN TIẾN ĐỘ CÔNG VIỆC HÔM NAY (17/10/2026)
**Dự án:** Aftercare-AI (Hệ thống Hỗ trợ Chăm sóc Hậu phẫu & Hen phế quản)

---

## 1. Mục Tiêu Thực Hiện Trong Ngày
1. Hoàn thiện việc phân tách cơ sở tri thức y khoa thành 2 phân hệ chuyên biệt (**Kho 1: Cảnh báo Cờ đỏ & Cấp cứu** và **Kho 2: Chăm sóc & Phục hồi tại nhà**).
2. Chuẩn hóa đánh chỉ mục số trang tài liệu gốc PDF (**Quyết định 1851/QĐ-BYT** và **GINA 2023**), tích hợp metadata hiển thị trích dẫn đúng trang tài liệu trên giao diện web.
3. Xây dựng và thực nghiệm Benchmark đánh giá hiệu năng truy xuất thông tin (IR Metrics) trên 20 Test Cases của Golden Dataset.
4. Triển khai thử nghiệm đánh giá chất lượng phản hồi lâm sàng qua bộ chỉ số RAGAS (Faithfulness, Answer Relevance, Context Precision/Recall) theo luồng Pure RAG.

---

## 2. Các Kết Quả Đã Đạt Được

### 2.1. Tái Cấu Trúc Tri Thức & Metadata PDF
- Đánh số trang PDF thực tế chính xác cho **192 chunks** tri thức y khoa.
- Tích hợp trường `document_tag`, `pdf_page`, `document_name` và `pdf_url` (hỗ trợ mở trực tiếp đúng trang PDF trên trình duyệt, ví dụ `#page=12`).
- Phân loại rõ ràng thuộc tính tri thức theo 2 phân kho lưu trữ trong cơ sở dữ liệu PgVector (`aftercare_db`).

### 2.2. Kết Quả Benchmark 4 Cấu Hình IR (Information Retrieval)
Đã đo kiểm tự động trên 20 test cases lâm sàng tiêu chuẩn:
- **Cấu hình 1 (Baseline - Dense toàn kho):** Hit Rate@3: 55.0% | Strict Recall@3: 35.0% | MRR@3: 0.442.
- **Cấu hình 2 (Phân hệ Dense Router):** Hit Rate@3: 55.0% | Strict Recall@3: 37.5% | MRR@3: 0.500.
- **Cấu hình 3 (Phân hệ Hybrid RRF - Dense + BM25):** Hit Rate@3: 75.0% | Strict Recall@3: 55.0% | MRR@3: 0.600.
- **Cấu hình 4 (Phân hệ Hybrid + Reranker BAAI/bge-reranker-large) 🏆:**
  - **Hit Rate@3:** Đạt **80.0%** (tăng +25% so với Baseline).
  - **Strict Recall@3:** Đạt **57.5%** (tăng +22.5% so với Baseline).
  - **MRR@3:** Đạt **0.683** (tăng +0.241 so với Baseline).
  - **Báo cáo chi tiết đã lưu:** [IR_BENCHMARK_REPORT.md](file:///home/hoangduc/Documents/Aftercare-AI/IR_BENCHMARK_REPORT.md).

### 2.3. Thử Nghiệm Luồng Pure RAG & Thẩm Định Lâm Sàng
- Cấu hình thử nghiệm luồng **Pure RAG 100%**: Mọi truy vấn đều qua vector retriever PgVector $\rightarrow$ Ghép System Prompt $\rightarrow$ Gọi LLM sinh phản hồi y khoa chuẩn.
- Đã kiểm tra tính khả thi của việc thẩm định:
  - Sinh phản hồi chuẩn lâm sàng bằng **Gemini Flash**.
  - Kiểm tra thẩm định độ trung thực (`Faithfulness`) và độ liên quan (`Answer Relevance`) qua mô hình giám khảo.
- Đã dọn dẹp các script tạm và báo cáo nháp RAGAS theo yêu cầu để chuẩn bị đo lường đồng bộ ở giai đoạn sau.

---

## 3. Kế Hoạch & Định Hướng Tiếp Theo
1. **Hoàn thiện UI/UX Web**: Tối ưu modal xem trước tài liệu PDF trực tiếp đúng trang trích dẫn khi người bệnh bấm vào nguồn tham khảo.
2. **Triển khai Reranker vào Backend**: Đưa pipeline Hybrid RRF + BGE Reranker (Cấu hình 4) thành pipeline tìm kiếm mặc định trong `service.py`.
3. **Đánh giá RAGAS toàn diện**: Thiết lập lại pipeline RAGAS khi có API key giám khảo ổn định để xuất bản báo cáo chất lượng sinh câu trả lời cho toàn bộ hệ thống.
