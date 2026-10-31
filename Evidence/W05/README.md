# Báo cáo Evidence Tuần 5 (W05): Bộ Sàng Lọc Triệu Chứng Rule-Based & Phân Tầng Mức Độ Nguy Cơ (Không Chẩn Đoán Bệnh)

**Cột mốc (Milestone):** `Tuan5`  
**Nhãn phiên bản (Tag):** `w05`  
**Dự án:** Aftercare-AI  

---

## 1. Mục tiêu tuần 5 (W05)
Xây dựng module **Symptom Screener rule-based** nhằm phân tầng mức độ nguy cơ lâm sàng (**Risk Levels**) với nguyên tắc an toàn cao nhất: **Tuyệt đối không chẩn đoán tên bệnh**, chỉ phân tầng nguy cơ khẩn cấp và hướng dẫn hành động xử trí tức thời dựa trên Kế hoạch hành động cá nhân (Action Plan) của bệnh nhân.

---

## 2. Phân công công việc (Theo dõi qua Git & Issue)

| Thành viên | Trách nhiệm chính | Issue & Pull Request | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Hoàng Ngọc Đức (Sinh viên A)** | **Backend & Động cơ sàng lọc triệu chứng:**<br>• Xây dựng bộ luật `SymptomScreenerEngine` (Cờ dấu hiệu báo động đỏ Red flags, ranh giới sinh hiệu: SpO2, PEF, nhịp thở).<br>• Phân tầng mức độ rủi ro: `RED_ZONE` (Nguy kịch), `YELLOW_ZONE` (Cảnh báo), `GREEN_ZONE` (Ổn định).<br>• Thiết lập rào chắn an toàn: Cam kết 100% không đưa ra chẩn đoán bệnh học (`Zero-Diagnosis Guarantee`).<br>• Xây dựng Endpoint API `/api/v1/screener/screen`. | **Issue #8:** Xây dựng động cơ sàng lọc triệu chứng rule-based và phân tầng mức độ nguy cơ<br>**PR #10**<br>*(Người duyệt PR: Nguyễn Trường Giang)* | **HOÀN THÀNH** |
| **Nguyễn Trường Giang (Sinh viên B)** | **Frontend & Bộ kiểm thử an toàn lâm sàng:**<br>• Thiết kế giao diện Sàng lọc nhanh triệu chứng cho người bệnh (Patient Screener Widget) và Bảng cảnh báo điều dưỡng (Nurse Station).<br>• Xây dựng bộ kiểm thử an toàn lâm sàng gồm 9 kịch bản (`test_symptom_screener.py`).<br>• Đánh giá chỉ số: Độ nhạy phát hiện triệu chứng cấp cứu đạt 100%, tỷ lệ tuân thủ không chẩn đoán đạt 100%.<br>• Đóng gói tài liệu và số liệu minh chứng vào thư mục `Evidence/W05`. | **Issue #9:** Xây dựng giao diện sàng lọc triệu chứng và bộ kiểm thử an toàn lâm sàng<br>**PR #11**<br>*(Người duyệt PR: Hoàng Ngọc Đức)* | **HOÀN THÀNH** |

---

## 3. Cấu trúc bộ luật & Tiêu chí phân tầng nguy cơ

### 3.1. Các mức độ nguy cơ (Risk Levels)
1. **RED_ZONE (Nguy kịch / Cấp cứu khẩn cấp):**
   - **Dấu hiệu:** SpO2 < 92%, PEF < 60% mức chuẩn cá nhân, môi/đầu chi tím tái, co kéo cơ hô hấp phụ, không nói được trọn câu, hoặc xịt thuốc cắt cơn nhưng không đỡ (kháng thuốc cắt cơn).
   - **Hành động:** Hướng dẫn gọi cấp cứu 115 ngay lập tức, sơ cứu khẩn cấp theo Kế hoạch hành động, đồng thời đẩy cảnh báo khẩn cấp đến Bảng trực điều dưỡng (Nurse Station).
2. **YELLOW_ZONE (Cảnh báo / Cần theo dõi sát):**
   - **Dấu hiệu:** SpO2 từ 92% đến 94%, PEF từ 60% đến 80%, tăng ho/đờm/khò khè nhưng chưa có dấu hiệu suy hô hấp nặng.
   - **Hành động:** Hướng dẫn xịt thuốc cắt cơn đúng liều quy định, nghỉ ngơi 20 phút rồi đo lại chỉ số, sẵn sàng liên hệ điều dưỡng nếu không cải thiện.
3. **GREEN_ZONE (Bình thường / Ổn định):**
   - **Dấu hiệu:** Mọi chỉ số sinh hiệu trong ngưỡng an toàn, triệu chứng được kiểm soát tốt.
   - **Hành động:** Tiếp tục duy trì thuốc điều trị đều đặn và sinh hoạt bình thường.

### 3.2. Rào chắn an toàn: Không chẩn đoán bệnh học
- Hệ thống chỉ cung cấp: **Mức độ khẩn cấp (Risk Level)**, **Cờ cảnh báo phát hiện (Matched Flags)**, và **Hướng dẫn hành động tức thì (Immediate Action Steps)**.
- Mọi kết quả phản hồi đều đính kèm tuyên bố miễn trừ y tế: *"Hệ thống hỗ trợ phân tầng mức độ khẩn cấp, tuyệt đối không thay thế chẩn đoán hoặc chỉ định trực tiếp từ bác sĩ chuyên khoa."*

---

## 4. Kết quả kiểm thử & Bảng chỉ số (Metrics)

- **Tổng số ca kiểm thử:** 9/9 kịch bản vượt qua thành công (100% PASSED).
- **Thời gian xử lý trung bình:** ~4.2 ms / lượt sàng lọc (xử lý tức thì bằng bộ luật rule-based).
- **Tập tin kết quả chi tiết:** Xem [`metrics.csv`](./metrics.csv) và [`test-results.txt`](./test-results.txt).
