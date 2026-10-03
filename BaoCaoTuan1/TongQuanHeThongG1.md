# TÀI LIỆU ĐẶC TẢ HỆ THỐNG CHĂM SÓC BỆNH NHÂN SAU XUẤT VIỆN (AFTERCARE-AI)

---

## MỤC 1: TỔNG QUAN HỆ THỐNG

### 1.1. Mục tiêu cốt lõi

Hệ thống giải quyết 2 bài toán chăm sóc bệnh nhân sau khi xuất viện:

1. **Medical RAG (Retrieval-Augmented Generation):** Trả lời các câu hỏi về chăm sóc sau xuất viện dựa trên nguồn chuyên môn đã được phê duyệt và luôn kèm trích dẫn (*citations*).
2. **Patient Risk Triage:** Đọc dữ liệu check-in, áp dụng luật an toàn (*Safety Rules*) và phân tích xu hướng để phân tầng rủi ro theo 3 mức **GREEN, YELLOW, RED**, từ đó ưu tiên các ca cần điều dưỡng can thiệp.

---

### 1.2. Bảng phân định phạm vi (System Scope)

| **Trong phạm vi hệ thống / AI (In-Scope)** | **Ngoài phạm vi hệ thống / AI (Out-of-Scope)** |
|---|---|
| **Medical RAG:** Trả lời câu hỏi chăm sóc sau xuất viện, có trích dẫn (*citation*). | Chẩn đoán hoặc quyết định điều trị thay nhân viên y tế. |
| **Safety Engine:** Dựa trên luật an toàn xác định (*deterministic rules*) và MEWS/NEWS2. | Tự ý kê đơn, thay đổi thuốc hoặc can thiệp y tế tự động. |
| **Phân tích xu hướng:** Theo dõi chỉ số sinh hiệu qua nhiều lần check-in. | Tự động gọi cấp cứu 115. |
| **Phân tầng rủi ro:** Đánh giá các mức **GREEN, YELLOW, RED**. | Tích hợp thiết bị IoT tại nhà. |
| **Escalation Protocol:** Sinh bản nháp báo cáo khi cần chuyển tuyến điều dưỡng. | Cam kết hiệu quả lâm sàng trên bệnh nhân thật. |
| **Guardrails y tế:** Ngăn chặn tuyệt đối việc tư vấn kê đơn, đổi liều hoặc chẩn đoán ngoài thẩm quyền. | Quản lý vòng đời điều trị nội trú tại bệnh viện. |
| **Quản lý dữ liệu bệnh nhân:** Check-in, Care Plan, Timeline sự kiện và lịch nhắc. | — |

---

### 1.3. Nguyên tắc vận hành cốt lõi (Core Operating Principles)

1. **Rule before model (Luật trước - Mô hình sau):**
   - Luật an toàn chạy trước và có quyền ưu tiên cao hơn mô hình AI.
   - Khi kích hoạt cờ **RED**, AI không được phép hạ mức cảnh báo xuống **YELLOW** hoặc **GREEN**.

2. **Fail-safe (An toàn khi có sự cố):**
   - Dữ liệu thiếu, mâu thuẫn hoặc lỗi hệ thống phải chuyển sang cho người có chuyên môn xử lý.
   - Hệ thống không được tự kết luận tình trạng an toàn khi dữ liệu không đủ tin cậy.

3. **Evidence before assertion (Bằng chứng trước khẳng định):**
   - Phản hồi y tế chỉ sử dụng nguồn tài liệu đã được kiểm duyệt và phải có trích dẫn rõ ràng.

4. **Human-in-the-loop (Con người can thiệp và kiểm soát):**
   - Mọi quyết định lâm sàng và xử lý cảnh báo **RED** bắt buộc phải do điều dưỡng / nhân viên y tế xác nhận và can thiệp.

---

## MỤC 2: PHẠM VI LÂM SÀNG VÀ CAN THIỆP

### 2.1. Phạm vi loại phẫu thuật hỗ trợ

Hệ thống chuẩn hóa kho tri thức RAG và bộ quy tắc an toàn lâm sàng riêng cho hai ca ngoại khoa vùng bụng:

- **Appendectomy:** Cắt ruột thừa do viêm ruột thừa cấp, gồm nội soi hoặc mổ hở.
- **Cholecystectomy:** Nội soi cắt túi mật do sỏi mật hoặc viêm túi mật.

---

### 2.2. Phạm vi can thiệp lâm sàng theo ngày hậu phẫu

- **Khung thời gian:** Tính từ ngày mổ và theo dõi trong **14 ngày hậu phẫu (POD 1 - POD 14)**.
- **Check-in hằng ngày (POD 1 - POD 14):**
  - Bệnh nhân trả lời form ngắn về mức đau, sốt, tình trạng vết mổ, ăn uống, trung/đại tiện và sinh hiệu nếu tự đo được.
  - Hệ thống gửi check-in vào giờ bệnh nhân ưu tiên.
- **Check-in mốc (POD 1, 3, 7, 14):**
  - Ngoài form hằng ngày, có thêm câu hỏi đánh giá theo từng giai đoạn.
- **Nhắc thuốc và tái khám:**
  - Gửi thông báo hằng ngày theo đơn xuất viện và cho phép bệnh nhân xác nhận đã uống.
  - Gửi nhắc lịch tái khám.

#### Giai đoạn và trọng tâm theo dõi

| Giai đoạn | Trọng tâm |
|---|---|
| **POD 1 - 3 — Hậu phẫu sớm** | Kiểm soát đau; phục hồi nhu động ruột (trung tiện, đại tiện); dung nạp dinh dưỡng từ lỏng sang đặc; theo dõi chảy máu hoặc dịch dẫn lưu. |
| **POD 4 - 7 — Hồi phục tại nhà** | Nhận diện nhiễm trùng vết mổ (sưng, nóng, đỏ, chảy mủ); tuân thủ thuốc giảm đau và kháng sinh theo toa. |
| **POD 8 - 14 — Hồi phục ổn định** | Tăng dần vận động; dinh dưỡng lành mạnh; nhắc lịch tái khám; đánh giá liền vết mổ. |

#### Xử lý không phản hồi (Missed Check-in Protocol)

1. Nhắc lại lần 1.
2. Nhắc lại lần 2.
3. Ghi nhận trạng thái bỏ lỡ.
4. **Escalation cho điều dưỡng** nếu:
   - Bệnh nhân bỏ lỡ **2 ngày liên tiếp**, hoặc
   - Bỏ lỡ một mốc **POD 1, POD 3 hoặc POD 7**.

---

## MỤC 3: AN TOÀN VÀ RANH GIỚI BẢO VỆ

### 3.1. Hàng rào phát hiện biến chứng và báo động đỏ (Red Flags)

Bộ quy tắc xác định chạy trước LLM ở mọi lượt check-in. Mỗi rule có mã và phiên bản để phục vụ truy vết.

#### Các dấu hiệu nguy cấp chung

- **Sốc / suy tuần hoàn:** Huyết áp tâm thu < 90 mmHg, mạch > 120 lần/phút, chóng mặt dữ dội hoặc ngất.
- **Suy hô hấp cấp:** Khó thở dữ dội, nhịp thở > 25 lần/phút, SpO₂ < 92%.
- **Biến chứng vết mổ:** Bung chỉ / hở mép vết mổ.
- **Tắc ruột / liệt ruột:** Nôn liên tục kèm bí trung đại tiện.

#### Cờ đỏ chuyên biệt

**Sau cắt túi mật:**

- Nghi rò dịch mật / tổn thương đường mật:
  - Đau quặn dữ dội vùng hạ sườn phải hoặc thượng vị.
  - Vàng mắt / vàng da tăng dần.
  - Sốt rét run, trong ma trận rule có ngưỡng > 38.5°C.

**Sau cắt ruột thừa:**

- Nghi áp-xe hoặc nhiễm trùng ổ bụng:
  - Sốt kéo dài hoặc tái phát.
  - Đau hố chậu phải tăng dần.
  - Báo cáo chỉ rõ nội dung rule cần được đối chiếu với nguồn y khoa công khai trước khi đưa vào rule chính thức.

#### Khi phát hiện cờ đỏ

1. Ngắt ngay luồng tư vấn thông thường.
2. Tự sinh bản nháp báo cáo.
3. Tạo ticket Escalation ưu tiên cao nhất lên dashboard điều dưỡng.
4. Hướng dẫn bệnh nhân gọi cấp cứu hoặc đến viện ngay.

---

### 3.2. Ranh giới an toàn y tế (Safety Boundaries)

#### Không được làm

- Không chẩn đoán bệnh.
- Không kê đơn mới.
- Không điều chỉnh liều hoặc hướng dẫn dừng thuốc ngoài đơn xuất viện đã duyệt.
- Không tự động gọi 115 hoặc kích hoạt dịch vụ cứu hộ.
- Không kết nối EMR/HIS bệnh viện thật.
- Không thay thế nhiệm vụ chuyên môn hoặc cam kết điều trị thay bác sĩ.

#### Nguyên tắc bắt buộc

- **Rule before model:** Luật an toàn chạy độc lập với LLM; LLM không được hạ mức rủi ro từ **RED** xuống **YELLOW** hoặc **GREEN**.
- **Human-in-the-loop:** Chỉ nhân viên y tế / điều dưỡng mới được đóng cảnh báo đỏ, kèm ghi chú xử lý lâm sàng.
- **Kế hoạch do bác sĩ lập:** Agent chỉ bám theo kế hoạch xuất viện đã duyệt và không tự thay đổi.
- **Grounded & Anti-hallucination:** Mọi khuyến nghị phải dựa trên kế hoạch xuất viện hoặc tài liệu chăm sóc có nguồn và kèm trích dẫn.
- **Dữ liệu mô phỏng:** Giai đoạn MVP chạy hoàn toàn trên dữ liệu mô phỏng.
- **Audit Trail:** Mỗi lần guardrail hoặc rule cờ đỏ kích hoạt đều phải được ghi log để chứng minh hệ thống hoạt động đúng.

---

### 3.3. Ma trận quy tắc an toàn và phát hiện nguy cơ theo giai đoạn

#### 3.3.1. Giai đoạn 1 — Hậu phẫu sớm (POD 1 - POD 3)

**Trọng tâm:** Kiểm soát đau sau mổ, theo dõi hồi phục nhu động ruột, khả năng dung nạp dinh dưỡng, phát hiện chảy máu nội hoặc rò mật.

| Mã quy tắc | Phân loại | Triệu chứng / Ngưỡng kích hoạt | Phân loại ca bệnh | Hành động xử lý |
|---|---|---|---|---|
| `EARLY-RED-01` | Sốc / Suy tuần hoàn | Huyết áp tâm thu < 90 mmHg **OR** mạch > 120 lần/phút **OR** chóng mặt dữ dội, ngất | Cả 2 ca | Kích hoạt **RED**, ngắt tư vấn tự động, sinh bản nháp báo cáo, yêu cầu cấp cứu / đến viện ngay |
| `EARLY-RED-02` | Nghi rò dịch mật | Đau quặn dữ dội hạ sườn phải / thượng vị + vàng mắt / vàng da tăng + sốt rét run (> 38.5°C) | Cắt túi mật | Kích hoạt **RED**, thông báo nguy cơ rò mật, báo điều dưỡng trực và hướng dẫn tới cơ sở y tế |
| `EARLY-RED-03` | Tắc ruột sớm / Liệt ruột | Nôn liên tục (> 3 lần/ngày), bụng trướng căng, bí trung đại tiện sau POD 2 | Cả 2 ca | Kích hoạt **RED**, ngừng ăn uống đường miệng, chuyển điều dưỡng xử lý gấp |
| `EARLY-YEL-01` | Kiểm soát đau kém | VAS ≥ 6/10 dù đã dùng thuốc giảm đau theo đơn xuất viện | Cả 2 ca | Ghi nhận **YELLOW**, nhắc nghỉ ngơi, gửi điều dưỡng xem xét điều chỉnh giảm đau |
| `EARLY-YEL-02` | Chậm hồi phục nhu động ruột | Chưa trung tiện sau POD 2, buồn nôn nhẹ khi ăn cháo lỏng | Cả 2 ca | Ghi nhận **YELLOW**, hướng dẫn vận động nhẹ nhàng tại chỗ, theo dõi sát check-in tiếp theo |

---

#### 3.3.2. Giai đoạn 2 — Hồi phục tại nhà (POD 4 - POD 7)

**Trọng tâm:** Phát hiện sớm nhiễm trùng vết mổ (Surgical Site Infection — SSI), áp-xe tồn lưu ổ bụng và theo dõi tuân thủ đơn thuốc kháng sinh.

| Mã quy tắc | Phân loại | Triệu chứng / Ngưỡng kích hoạt | Phân loại ca bệnh | Hành động xử lý |
|---|---|---|---|---|
| `MID-RED-01` | Nhiễm trùng vết mổ nặng / Bung vết mổ | Vết mổ chảy mủ đục, mùi hôi **OR** bung chỉ, hở mép vết mổ **OR** sốt cao > 38.5°C liên tục 2 ngày | Cả 2 ca | Kích hoạt **RED**, hướng dẫn giữ sạch vết mổ, yêu cầu tái khám ngay, tạo ticket chuyển tuyến |
| `MID-RED-02` | Nghi áp-xe ổ bụng / Viêm phúc mạc | Đau hố chậu phải / hạ sườn phải tăng dần + sốt dao động + bụng cứng, đau khi chạm | Cắt ruột thừa / cắt túi mật | Kích hoạt **RED**, chuyển hồ sơ ngay cho điều dưỡng / bác sĩ, hướng dẫn nhập viện kiểm tra |
| `MID-YEL-01` | Viêm nhẹ quanh vết mổ | Vết mổ sưng nhẹ, hơi đỏ mép, không rỉ dịch đục, sốt nhẹ (< 38°C) | Cả 2 ca | Ghi nhận **YELLOW**, hướng dẫn vệ sinh vết mổ theo RAG, yêu cầu chụp ảnh vết mổ gửi điều dưỡng |
| `MID-YEL-02` | Không tuân thủ đơn thuốc | Bỏ lỡ liều kháng sinh hoặc tự ý ngưng thuốc khi chưa hết đơn | Cả 2 ca | Ghi nhận **YELLOW**, tư vấn RAG về tuân thủ kháng sinh và nguy cơ kháng thuốc |

---

#### 3.3.3. Giai đoạn 3 — Hồi phục ổn định (POD 8 - POD 14)

**Trọng tâm:** Đánh giá liền vết mổ, nâng dần vận động, dinh dưỡng trở lại bình thường và tuân thủ lịch tái khám ngoại trú.

| Mã quy tắc | Phân loại | Triệu chứng / Ngưỡng kích hoạt | Phân loại ca bệnh | Hành động xử lý |
|---|---|---|---|---|
| `LATE-RED-01` | Nhiễm trùng muộn / Rò vết mổ | Vết mổ chảy dịch dai dẳng, sốt tái phát, đau bụng dữ dội đột ngột | Cả 2 ca | Kích hoạt **RED**, yêu cầu tái khám ngay với bác sĩ phẫu thuật |
| `LATE-YEL-01` | Chậm lành vết mổ / Rối loạn tiêu hóa | Vết mổ còn ngứa, đóng vảy kém **OR** tiêu chảy nhẹ dai dẳng sau mổ túi mật | Cả 2 ca | Ghi nhận **YELLOW**, hướng dẫn chế độ ăn giảm mỡ với cắt túi mật và theo dõi thêm |
| `LATE-YEL-02` | Quên / Trễ tái khám | Chưa xác nhận lịch hẹn tái khám tại mốc POD 7 / POD 14 | Cả 2 ca | Ghi nhận **YELLOW**, gửi nhắc lịch tái khám và hướng dẫn đặt lịch |
| `LATE-GRN-01` | Hồi phục tốt | Không đau, không sốt, vết mổ khô lành tốt, sinh hoạt và ăn uống bình thường | Cả 2 ca | Đánh giá **GREEN**, gửi lời chúc mừng, dặn dò vận động nặng và hoàn tất chương trình theo dõi |

---

### 3.4. Phân cấp mức độ ưu tiên Ticket (Escalation Priority)

Hệ thống phân loại sự cố và cảnh báo chuyển tiếp thành 4 cấp độ ưu tiên:

| Cấp độ | Tên gọi | Định nghĩa lâm sàng / vận hành | SLA phản hồi ban đầu | SLA xử lý / đóng ticket | Người chịu trách nhiệm chính |
|---|---|---|---:|---:|---|
| `P0_CRITICAL` | Khẩn cấp đe dọa tính mạng | Red Flag: sốc, suy hô hấp, rò mật, áp-xe ổ bụng, tắc ruột, bung vết mổ | ≤ 15 phút | ≤ 30 phút | Điều dưỡng trực cấp cứu + Bác sĩ phẫu thuật chính |
| `P1_HIGH` | Nguy cơ cao / Mất liên lạc | Bỏ lỡ mốc then chốt (POD 1, 3, 7), không phản hồi 2 ngày liên tiếp, đau dữ dội kháng thuốc | ≤ 60 phút | ≤ 120 phút | Điều dưỡng phụ trách theo dõi ngoại khoa |
| `P2_MEDIUM` | Cảnh báo lâm sàng — Yellow | Yellow Flag: viêm nhẹ mép vết mổ, chậm nhu động ruột, bỏ cữ kháng sinh, tiêu chảy nhẹ | ≤ 240 phút (4 giờ) | ≤ 8 giờ | Điều dưỡng theo dõi ngoại trú |
| `P3_LOW` | Yêu cầu hỗ trợ thông tin | Quên lịch tái khám, thắc mắc sinh hoạt vượt phạm vi tài liệu RAG, cập nhật hành chính | ≤ 24 giờ | ≤ 48 giờ | Trợ lý điều phối chăm sóc / Điều dưỡng hành chính |

---

## MỤC 4: SCHEMA CƠ SỞ DỮ LIỆU

### 4.1. Bảng `users` — Người dùng hệ thống

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã định danh duy nhất |
| `full_name` | VARCHAR(255) | NOT NULL | Họ và tên |
| `phone_number` | VARCHAR(20) | UNIQUE, NOT NULL | Số điện thoại đăng nhập / liên hệ |
| `email` | VARCHAR(255) | UNIQUE | Địa chỉ email |
| `role` | UserRole | NOT NULL | Vai trò trong hệ thống |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Thời gian tạo tài khoản |

### 4.2. Bảng `patients` — Hồ sơ bệnh nhân

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã hồ sơ bệnh nhân |
| `user_id` | UUID | FK → `users.id` | Khóa ngoại tham chiếu người dùng |
| `dob` | DATE | NOT NULL | Ngày sinh |
| `gender` | VARCHAR(10) | — | Giới tính |
| `emergency_contact` | JSONB | — | Thông tin người thân khẩn cấp |

### 4.3. Bảng `care_plans` — Kế hoạch chăm sóc xuất viện

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã kế hoạch chăm sóc |
| `patient_id` | UUID | FK → `patients.id` | Bệnh nhân thụ hưởng |
| `surgery_type` | SurgeryType | NOT NULL | Loại phẫu thuật (ruột thừa / túi mật) |
| `surgery_date` | DATE | NOT NULL | Ngày phẫu thuật (POD 0) |
| `discharge_date` | DATE | NOT NULL | Ngày xuất viện |
| `status` | CarePlanStatus | DEFAULT ACTIVE | Trạng thái kế hoạch |

### 4.4. Bảng `medications` — Danh mục đơn thuốc xuất viện

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã thuốc trong đơn |
| `care_plan_id` | UUID | FK → `care_plans.id` | Mã kế hoạch chăm sóc |
| `medication_name` | VARCHAR(255) | NOT NULL | Tên biệt dược / hoạt chất |
| `dosage` | VARCHAR(100) | NOT NULL | Liều dùng, ví dụ `500mg` |
| `frequency` | VARCHAR(100) | NOT NULL | Tần suất uống, ví dụ `2 lần/ngày` |
| `instructions` | TEXT | — | Hướng dẫn thêm (sau ăn, trước ngủ...) |

### 4.5. Bảng `follow_up_appointments` — Lịch hẹn tái khám

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã lịch hẹn |
| `care_plan_id` | UUID | FK → `care_plans.id` | Kế hoạch chăm sóc tương ứng |
| `appointment_date` | TIMESTAMP | NOT NULL | Thời gian tái khám |
| `location` | VARCHAR(255) | — | Địa điểm / Phòng khám |
| `status` | VARCHAR(50) | DEFAULT `SCHEDULED` | Trạng thái lịch hẹn |

### 4.6. Bảng `care_plan_versions` — Lịch sử phiên bản kế hoạch chăm sóc

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã phiên bản |
| `care_plan_id` | UUID | FK → `care_plans.id` | Kế hoạch chăm sóc gốc |
| `version_number` | INT | NOT NULL | Số phiên bản (1, 2, 3...) |
| `snapshot_data` | JSONB | NOT NULL | Dữ liệu snapshot của toàn bộ CarePlan |
| `updated_by` | UUID | FK → `users.id` | Người phê duyệt / chỉnh sửa |

### 4.7. Bảng `care_guideline_documents` — Tài liệu hướng dẫn chuyên môn RAG

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã tài liệu |
| `title` | VARCHAR(255) | NOT NULL | Tiêu đề tài liệu y khoa |
| `category` | SurgeryType | NOT NULL | Phân loại theo ca phẫu thuật |
| `source_url` | TEXT | — | Đường dẫn nguồn tài liệu đã duyệt |
| `is_active` | BOOLEAN | DEFAULT TRUE | Cờ cho phép sử dụng trong RAG |

### 4.8. Bảng `document_chunks` — Đoạn tài liệu đã Chunking & Vectorize

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã chunk |
| `document_id` | UUID | FK → `care_guideline_documents.id` | Tài liệu gốc |
| `content` | TEXT | NOT NULL | Nội dung văn bản đoạn cắt |
| `embedding` | VECTOR(1536) | — | Vector embedding phục vụ tìm kiếm RAG |

### 4.9. Bảng `checkins` — Phiên check-in của bệnh nhân

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã phiên check-in |
| `care_plan_id` | UUID | FK → `care_plans.id` | Kế hoạch chăm sóc liên quan |
| `pod_day` | INT | NOT NULL | Ngày hậu phẫu thứ n (POD 1-14) |
| `responses` | JSONB | — | Câu trả lời form check-in & sinh hiệu |
| `risk_level` | RiskLevel | — | Mức rủi ro do Safety Engine / AI đánh giá |
| `status` | CheckinStatus | DEFAULT `SCHEDULED` | Trạng thái hoàn thành check-in |

### 4.10. Bảng `escalations` — Phiếu chuyển tuyến / Báo động đỏ

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã escalation ticket |
| `checkin_id` | UUID | FK → `checkins.id` | Check-in phát sinh cảnh báo |
| `priority` | EscalationPriority | NOT NULL | Mức độ ưu tiên xử lý |
| `triggered_rules` | JSONB | NOT NULL | Mã các luật cờ đỏ bị kích hoạt |
| `draft_report` | TEXT | — | Bản nháp báo cáo tự sinh cho điều dưỡng |
| `status` | EscalationStatus | DEFAULT `OPEN` | Trạng thái ticket |
| `resolved_by` | UUID | FK → `users.id` | Điều dưỡng / bác sĩ xử lý ticket |

### 4.11. Bảng `timeline_events` — Dòng thời gian sự kiện bệnh nhân

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã sự kiện timeline |
| `patient_id` | UUID | FK → `patients.id` | Bệnh nhân liên quan |
| `event_type` | VARCHAR(100) | NOT NULL | Loại sự kiện (Checkin, Alert, Med...) |
| `event_data` | JSONB | — | Chi tiết sự kiện |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Thời gian diễn ra sự kiện |

### 4.12. Bảng `notifications` — Lịch sử gửi thông báo

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã thông báo |
| `user_id` | UUID | FK → `users.id` | Người nhận thông báo |
| `channel` | NotificationChannel | NOT NULL | Kênh gửi (Zalo, Push, SMS...) |
| `message` | TEXT | NOT NULL | Nội dung tin nhắn |
| `sent_at` | TIMESTAMP | — | Thời điểm gửi thực tế |

### 4.13. Bảng `agent_actions_log` — Nhật ký hành động của AI Agent

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã log AI Agent |
| `care_plan_id` | UUID | FK → `care_plans.id` | Kế hoạch chăm sóc liên quan |
| `prompt_tokens` | INT | — | Số lượng token đầu vào |
| `completion_tokens` | INT | — | Số lượng token đầu ra |
| `retrieved_chunks` | JSONB | — | Danh sách các chunk RAG được trích xuất |
| `output_response` | TEXT | — | Phản hồi do LLM sinh ra |

### 4.14. Bảng `audit_logs` — Nhật ký truy vết an toàn & Guardrails

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Mã log kiểm toán |
| `action` | VARCHAR(100) | NOT NULL | Hành động kiểm toán, ví dụ `GUARDRAIL_TRIGGERED` |
| `actor_id` | UUID | — | ID của người dùng hoặc System Agent |
| `details` | JSONB | NOT NULL | Chi tiết bằng chứng guardrail / rule kích hoạt |
| `created_at` | TIMESTAMP | — | Thời gian ghi log |

---

## MỤC 5: KỊCH BẢN XUẤT VIỆN GIẢ LẬP (DISCHARGE SCENARIOS)

### 5.1. Kịch bản 1: Phẫu thuật cắt ruột thừa cấp (Appendectomy)

#### 5.1.1. Hồ sơ bệnh nhân giả lập

- **Mã ca:** `SCENARIO_APP_ACUTE_01`
- **Loại phẫu thuật:** Cắt ruột thừa nội soi do viêm ruột thừa cấp sung huyết chưa vỡ.
- **Thời điểm xuất viện:** POD 1 (24 giờ sau mổ).
- **Đặc điểm lâm sàng lúc xuất viện:**
  - Mạch: 78 lần/phút.
  - Huyết áp: 115/75 mmHg.
  - SpO₂: 98%.
  - Thân nhiệt: 36.8°C.
  - Bụng mềm.
  - Ấn đau nhẹ hố chậu phải, VAS 3/10.
  - Đã trung tiện nhẹ, chưa đại tiện.
  - Vết mổ nội soi 3 lỗ khô sạch.

#### 5.1.2. Kế hoạch chăm sóc và lịch trình can thiệp (POD 1 - POD 14)

| Giai đoạn | Trọng tâm lâm sàng | Nhiệm vụ của Agent |
|---|---|---|
| **POD 1 - 3** | Kiểm soát đau vết mổ; phục hồi nhu động ruột; chuyển thức ăn từ lỏng sang đặc; theo dõi rỉ dịch vết mổ. | Daily Check-in lúc 08:30; Milestone POD 1 về đau vai do khí CO₂ và dịch rỉ; POD 3 xác nhận đại tiện và dung nạp cơm mềm; nhắc Cefuroxime và Paracetamol theo lịch. |
| **POD 4 - 7** | Phát hiện nhiễm trùng vết mổ nông/sâu; áp-xe tồn lưu ổ bụng; kiểm tra hoàn thành kháng sinh. | Daily Check-in hàng ngày; kiểm tra uống hết cữ kháng sinh ngày 5; Milestone POD 7 đánh giá vết mổ và nhắc tái khám. |
| **POD 8 - 14** | Nâng dần cường độ vận động; dinh dưỡng bình thường; xác nhận kết quả tái khám; liền mép sẹo. | Daily Check-in hàng ngày; POD 10 xác nhận đã tái khám; Milestone POD 14 đánh giá tổng kết vận động và kết thúc 14 ngày giám sát. |

#### 5.1.3. Các nhánh tương tác giả lập (Simulation Paths)

##### Nhánh A — Tiến triển thuận lợi (Nominal Pathway)

- **POD 1:** Đau VAS 3, nhiệt độ 37.0°C, vết mổ khô, uống sữa và cháo loãng tốt, đã trung tiện. Agent gửi phản hồi khích lệ, hướng dẫn vận động đi lại nhẹ nhàng và nhắc uống thuốc đúng cữ sáng.
- **POD 3:** Đại tiện phân mềm lần đầu, bắt đầu ăn cơm nát, không nôn, đau giảm còn VAS 2. Agent xác nhận tiêu hóa hồi phục đúng lộ trình.
- **POD 7:** Vết mổ khép mép tốt, không đỏ, hết thuốc kháng sinh. Agent nhắc bệnh nhân đến viện tái khám vào sáng ngày hôm sau theo lịch hẹn.
- **POD 14:** Bệnh nhân sinh hoạt bình thường, không biến chứng. Hệ thống đóng hồ sơ theo dõi.

##### Nhánh B — Nghi áp-xe tồn lưu ổ bụng (Red Flag Pathway)

**Thời điểm kích hoạt:** Chiều POD 5.

**Đầu vào bệnh nhân:**

> "Từ chiều qua đến giờ tôi bị sốt rét run lại, đo nhiệt kế 38.8 độ C, bụng bên hố chậu phải đau nhói tăng dần, uống 2 viên Paracetamol rồi mà không hạ sốt."

**Xử lý kỹ thuật của hệ thống:**

1. **Deterministic Rule Engine — Layer 1:** Kích hoạt `MID-RED-02` (nghi áp-xe hoặc nhiễm trùng ổ bụng sâu) theo logic trong báo cáo: sốt ≥ 38.5°C sau POD 3 + đau tăng dần vùng hố chậu phải + không đáp ứng hạ sốt.
2. **Ngắt luồng Agent:** Cô lập phiên hội thoại thông thường, không chuyển context vào mô hình LLM mở.
3. **Tạo Ticket Escalation:** Mức `P0_CRITICAL`, tự động sinh báo cáo lâm sàng lên Dashboard điều dưỡng:
   - Bệnh nhân `SIM-PAT-0101`
   - POD 5, cắt ruột thừa.
   - Sốt 38.8°C tái phát.
   - Đau nhói hố chậu phải tăng dần.
   - Không đáp ứng thuốc hạ sốt.
4. **Phản hồi người bệnh:** Cảnh báo an toàn, yêu cầu đến khoa Cấp cứu / cơ sở y tế hoặc gọi 115 để được bác sĩ thăm khám trực tiếp; không tự ý uống thêm thuốc.
5. **Ghi Audit Log:** Ghi toàn bộ chuỗi sự kiện, mã rule, timestamp và trạng thái ticket chờ nhân viên y tế xử lý.

---

### 5.2. Kịch bản 2: Phẫu thuật cắt túi mật nội soi (Cholecystectomy)

#### 5.2.1. Hồ sơ bệnh nhân giả lập

- **Mã ca:** `null` (theo báo cáo nguồn).
- **Loại phẫu thuật:** Cắt túi mật nội soi do sỏi túi mật tái phát nhiều đợt.
- **Thời điểm xuất viện:** POD 1 (24 giờ sau mổ).
- **Đặc điểm lâm sàng lúc xuất viện:**
  - Mạch: 72 lần/phút.
  - Huyết áp: 120/80 mmHg.
  - SpO₂: 99%.
  - Thân nhiệt: 36.6°C.
  - 4 vết mổ nội soi vùng rốn và hạ sườn phải khô.
  - Không dẫn lưu.
  - Đau tức nhẹ hạ sườn phải và mỏi cơ vai phải, VAS 4/10 do khí CO₂.

#### 5.2.2. Kế hoạch chăm sóc và lịch trình can thiệp (POD 1 - POD 14)

| Giai đoạn | Trọng tâm lâm sàng | Nhiệm vụ của Agent |
|---|---|---|
| **POD 1 - 3** | Đánh giá hội chứng đau vai do ứ khí CO₂; loại trừ tổn thương đường mật / rò mật sớm; dung nạp thức ăn lỏng không béo. | Daily Check-in lúc 08:30; Milestone POD 1 tách biệt đau vết mổ với đau vai do CO₂; giám sát đau hạ sườn phải, sốt, vàng mắt, màu sắc nước tiểu. |
| **POD 4 - 7** | Giám sát liền vết mổ; kiểm soát triệu chứng tiêu hóa sau cắt túi mật; nhận diện viêm đường mật muộn. | Daily Check-in; nhắc chế độ ăn giảm chất béo; Milestone POD 7 kiểm tra 4 vết mổ và nhắc tái khám. |
| **POD 8 - 14** | Thích nghi chế độ ăn uống mở rộng; tăng cường vận động thể lực; kiểm tra chỉ khâu và xác nhận tái khám. | Daily Check-in; POD 10 theo dõi tình trạng phân và dung nạp mỡ; Milestone POD 14 đánh giá hoàn thành phục hồi thể chất. |

#### 5.2.3. Các nhánh tương tác giả lập (Simulation Paths)

##### Nhánh A — Tiến triển thuận lợi (Nominal Pathway)

- **POD 1:** Đau mỏi vai phải VAS 4, vết mổ đau nhẹ VAS 2, không sốt. Agent giải thích dựa trên cẩm nang RAG rằng đau vai có thể xuất hiện sau mổ nội soi do kích thích cơ hoành bởi khí CO₂ và thường giảm dần sau 2-3 ngày khi vận động nhẹ.
- **POD 3:** Đau vai hết hoàn toàn, ăn cháo thịt nạc không buồn nôn, đại tiện bình thường.
- **POD 7:** 4 vết rạch khô hoàn toàn, không vàng da. Bệnh nhân đi tái khám đúng hẹn.
- **POD 14:** Hoàn tất 14 ngày theo dõi.

##### Nhánh B — Nghi rò dịch mật / Tổn thương đường mật (Red Flag Pathway)

**Thời điểm kích hoạt:** Sáng POD 3.

**Đầu vào bệnh nhân qua Daily Form:**

- Mức đau: **8/10**, đau quặn dữ dội hạ sườn phải lan ra sau lưng.
- Thân nhiệt: **38.6°C**, kèm rét run.
- Tròng trắng mắt có ánh vàng nhẹ.
- Nước tiểu sẫm màu như nước trà đặc.
- Nôn 2 lần sau uống nước.

**Xử lý kỹ thuật của hệ thống:**

1. **Deterministic Rule Engine — Layer 1:** Kích hoạt quy tắc `MID-RED-03` về nghi rò dịch mật hoặc tổn thương đường mật.
2. **Tác vụ hệ thống:** Dừng ngay quy trình check-in tự động và tạo Ticket `P0_CRITICAL` cho điều dưỡng ngoại khoa và bác sĩ phẫu thuật chính.
3. **Nội dung ticket:** Bệnh nhân `SIM-PAT-0102`, POD 3 cắt túi mật, nghi rò mật / viêm phúc mạc mật; triệu chứng gồm đau quặn hạ sườn phải VAS 8, sốt 38.6°C rét run, vàng mắt, nước tiểu sẫm màu và nôn mửa.
4. **Cảnh báo giao diện bệnh nhân:** Thông báo rằng các triệu chứng là dấu hiệu nghi ngờ biến chứng đường mật sau phẫu thuật và cần can thiệp y tế tức thời; yêu cầu đến khoa Cấp cứu / cơ sở y tế gần nhất.
5. **Human-in-the-loop:** Giao diện Agent bị khóa đối với bệnh nhân cho đến khi điều dưỡng trực xác nhận đã liên hệ và bệnh nhân đang được đưa đến viện.

---

## MỤC 6: NGUYÊN TẮC TRIỂN KHAI VÀ KIỂM TOÁN

### 6.1. Luồng xử lý tổng quát

```text
Bệnh nhân gửi Check-in
        |
        v
Deterministic Safety Rules
        |
        +---- RED ----> Ngắt LLM
        |                |
        |                +--> Tạo P0 Escalation
        |                +--> Sinh Draft Report
        |                +--> Hướng dẫn đi cấp cứu / đến viện
        |                +--> Ghi Audit Log
        |
        +---- YELLOW --> Ghi nhận cảnh báo
        |                +--> Theo dõi / Escalation theo SLA
        |                +--> RAG khi phù hợp
        |
        +---- GREEN ---> Tiếp tục theo dõi
                         +--> RAG / nhắc lịch
                         +--> Hoàn tất chương trình nếu đủ điều kiện
```

### 6.2. Nguyên tắc ưu tiên xử lý

- Safety Engine phải được thực thi trước LLM.
- LLM không được ghi đè kết quả RED của Safety Engine.
- Khi dữ liệu thiếu hoặc mâu thuẫn, phải chuyển sang xử lý bởi người có chuyên môn.
- Các phản hồi y tế phải grounded vào Care Plan hoặc tài liệu RAG đã được duyệt.
- Các quyết định lâm sàng phải có Human-in-the-loop.
- Toàn bộ rule kích hoạt, guardrail và hành động của Agent phải có khả năng truy vết qua log.

### 6.3. Trạng thái MVP

- Hệ thống MVP sử dụng **dữ liệu mô phỏng (synthetic data)**.
- Không kết nối EMR/HIS bệnh viện thật.
- Không tự động gọi 115.
- Không thực hiện chẩn đoán, kê đơn hoặc thay đổi điều trị.
- Các rule lâm sàng cần được đối chiếu và phê duyệt từ nguồn y khoa phù hợp trước khi sử dụng trong môi trường thực tế.
