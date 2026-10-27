# EVIDENCE TUẦN 04 (WEEK 04) - AFTERCARE-AI

- **Dự án:** Aftercare-AI (Hệ thống RAG Chăm sóc & Hướng dẫn Sau xuất viện cho Bệnh nhân Hen Phế quản)
- **Milestone:** Tuan4
- **Tag:** `w04`

---

## 1. MỤC TIÊU VÀ NHIỆM VỤ TUẦN 04

Trong tuần 4, nhóm tập trung vào hai mảng công việc cốt lõi:
1. **Kiểm thử & Đánh giá định lượng RAG (Clinical RAGAS Evaluation):**
   - Xây dựng quy trình đánh giá chuẩn lâm sàng với 4 tiêu chí cốt lõi: Context Recall, Context Precision, Faithfulness, Answer Relevance trên bộ 20 Test Cases chuẩn tiếng Việt (`Data/golden_dataset.json`).
   - Sử dụng Judge LLM (`openai/gpt-4o`) và Generator (`google/gemini-2.5-flash`).
2. **Xây dựng Care Plan Tracker & Medication Reminder:**
   - Hoàn thiện mô hình dữ liệu, migration bảng PostgreSQL cho Kế hoạch hành động hen (Care Plan).
   - Xây dựng giao diện Check-in triệu chứng hàng ngày, banner cảnh báo dùng thuốc và nhắc lịch khám.

---

## 2. PHÂN CÔNG VÀ LIÊN KẾT GITHUB (ISSUES & PR)

| STT | Thành viên | Nhiệm vụ chính (Deliverable) | Issue liên kết | Pull Request & Reviewer |
| :---: | :---: | :--- | :---: | :---: |
| 1 | **Hoàng Ngọc Đức** | Thiết kế bộ đánh giá RAGAS tiếng Việt, thu thập số liệu 20 Test Cases | Issue #xx | PR #xx (Reviewer: Nguyễn Trường Giang) |
| 2 | **Nguyễn Trường Giang** | Xây dựng API và giao diện Care Plan Tracker, Check-in & Lịch uống thuốc | Issue #yy | PR #yy (Reviewer: Hoàng Ngọc Đức) |

---

## 3. TỔNG HỢP KẾT QUẢ ĐẠT ĐƯỢC (METRICS SUMMARY)

Bảng tổng hợp từ file `metrics.csv` và `test-results.json`:

| Chỉ số đánh giá | Kết quả thực tế | Tỷ lệ % |
| :--- | :---: | :---: |
| **Số Test Cases hoàn thành** | **20 / 20** | **100%** |
| **Context Recall** | **0.7500** | **75.00%** |
| **Context Precision** | **0.6667** | **66.67%** |
| **Faithfulness** | **0.9950** | **99.50%** |
| **Answer Relevance** | **0.9500** | **95.00%** |

---

## 4. DANH MỤC TỆP MINH CHỨNG (EVIDENCE ARTIFACTS)

Toàn bộ các tệp minh chứng tuần 4 được tổ chức tại thư mục `Evidence/W04/`:

- **`manifest.json`**: Tệp kê khai metadata toàn bộ deliverables và cấu trúc minh chứng tuần 4.
- **`metrics.csv`**: Dữ liệu số liệu thô theo từng Test Case (TC01 đến TC20) và dòng tổng hợp trung bình.
- **`test-results.json`**: File kết quả benchmark đầy đủ gồm câu hỏi, chunks truy xuất, đáp án sinh ra và vết đánh giá (judge trace).
- **`figures/`**:
  - `figures/ragas_metrics_overview.png`: Biểu đồ cột tổng quan 4 chỉ số RAGAS.
  - `figures/ragas_per_testcase_breakdown.png`: Biểu đồ chi tiết từng Test Case (TC01 - TC20).
