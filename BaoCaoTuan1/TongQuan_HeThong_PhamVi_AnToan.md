# TÀI LIỆU ĐẶC TẢ HỆ THỐNG CHĂM SÓC BỆNH NHÂN SAU XUẤT VIỆN (AFTERCARE-AI)

---

## MỤC 1: TỔNG QUAN HỆ THỐNG

### 1.1. Mục tiêu cốt lõi
Hệ thống giải quyết 2 bài toán trọng tâm trong việc chăm sóc bệnh nhân sau khi xuất viện:
1. **Medical RAG (Retrieval-Augmented Generation):** Trả lời các câu hỏi về chăm sóc sau xuất viện dựa trên nguồn tài liệu chuyên môn y khoa đã được phê duyệt, luôn đi kèm trích dẫn nguồn rõ ràng.
2. **Patient Risk Triage (Phân tầng rủi ro bệnh nhân):** Tiếp nhận và đọc dữ liệu check-in định kỳ, áp dụng bộ luật an toàn lâm sàng xác định kết hợp phân tích xu hướng để phân tầng rủi ro theo thang 3 mức (**GREEN**, **YELLOW**, **RED**), từ đó tối ưu và ưu tiên các ca bệnh cần can thiệp y tế khẩn cấp từ đội ngũ điều dưỡng.

---

### 1.2. Bảng phân định phạm vi (System Scope)

| Trong phạm vi hệ thống / AI (In-Scope) | Ngoài phạm vi hệ thống / AI (Out-of-Scope) |
| :--- | :--- |
| **Medical RAG:** Trả lời câu hỏi chăm sóc sau xuất viện, bắt buộc có trích dẫn nguồn. | **Chẩn đoán hoặc quyết định điều trị** thay thế cho nhân viên y tế / bác sĩ. |
| **Safety Engine:** Dựa trên luật an toàn xác định và thang điểm sinh hiệu (MEWS/NEWS2). | **Tự ý kê đơn**, thay đổi thuốc, chỉnh liều hoặc can thiệp y tế tự động. |
| **Phân tích xu hướng:** Theo dõi liên tục các chỉ số sinh hiệu và mức độ triệu chứng qua nhiều lượt check-in. | **Tự động gọi cấp cứu 115** hay kích hoạt dịch vụ cứu hộ khẩn cấp trực tiếp. |
| **Phân tầng rủi ro:** Đánh giá và gắn nhãn theo các mức cảnh báo **GREEN**, **YELLOW**, **RED**. | **Tích hợp phần cứng thiết bị IoT** chuyên sâu tại nhà (giai đoạn hiện tại). |
| **Escalation Protocol:** Tự động sinh bản nháp báo cáo tóm tắt khi cần chuyển tuyến điều dưỡng can thiệp. | **Cam kết hiệu quả điều trị lâm sàng** trên bệnh nhân thực tế ngoài đời sống. |
| **Guardrails y tế:** Ngăn chặn tuyệt đối hành vi tư vấn kê đơn, đổi liều hoặc chẩn đoán ngoài thẩm quyền. | **Quản lý toàn diện vòng đời điều trị nội trú** trong bệnh viện. |
| **Quản lý dữ liệu bệnh nhân ngoại trú:** Theo dõi check-in, Kế hoạch chăm sóc, Timeline sự kiện và lịch nhắc nhở. | - |

---

### 1.3. Nguyên tắc vận hành cốt lõi (Core Operating Principles)

1. **Rule before model (Luật trước - Mô hình sau):**
   - Bộ quy tắc an toàn lâm sàng xác định (*deterministic rules*) chạy trước và có quyền ưu tiên tuyệt đối so với mô hình AI.
   - Khi cờ Đỏ (**RED**) đã được kích hoạt bởi luật, AI tuyệt đối không có quyền hạ mức cảnh báo xuống Vàng (**YELLOW**) hoặc Xanh (**GREEN**).
2. **Fail-safe (An toàn khi có sự cố):**
   - Khi dữ liệu check-in bị thiếu, mâu thuẫn bất thường hoặc hệ thống gặp sự cố kỹ thuật, hệ thống phải tự động điều hướng sang cho nhân viên chuyên môn xử lý, tuyệt đối không tự ý giả định là an toàn.
3. **Evidence before assertion (Bằng chứng trước khẳng định):**
   - Mọi thông tin phản hồi và hướng dẫn y tế chỉ được phép sử dụng từ các nguồn tài liệu đã được kiểm duyệt chuyên môn và bắt buộc phải trích dẫn nguồn rõ ràng.
4. **Human-in-the-loop (Con người can thiệp và kiểm soát):**
   - Mọi quyết định lâm sàng và việc xử lý/đóng cảnh báo Đỏ bắt buộc phải do điều dưỡng hoặc nhân viên y tế có thẩm quyền xác nhận và thực hiện can thiệp.

---

## MỤC 2: PHẠM VI LÂM SÀNG VÀ CAN THIỆP

### 2.1. Phạm vi loại phẫu thuật hỗ trợ
Hệ thống chuẩn hóa kho tri thức RAG và bộ quy tắc an toàn lâm sàng chuyên biệt cho 2 ca can thiệp ngoại khoa vùng bụng phổ biến:
- **Appendectomy:** Phẫu thuật cắt ruột thừa do viêm ruột thừa cấp (bao gồm phẫu thuật nội soi hoặc mổ hở).
- **Cholecystectomy:** Phẫu thuật nội soi cắt túi mật (do sỏi túi mật, viêm túi mật).

---

### 2.2. Phạm vi can thiệp lâm sàng theo ngày hậu phẫu
- **Khung thời gian:** Tính từ ngày phẫu thuật và theo dõi liên tục trong vòng **14 ngày hậu phẫu (POD 1 - POD 14)**.
- **Check-in hằng ngày (POD 1 - POD 14):** 
  - Bệnh nhân hoàn thành biểu mẫu ngắn: mức độ đau (thang điểm 1-10), nhiệt độ/sốt, tình trạng vết mổ, khả năng ăn uống dung nạp, tình trạng trung/đại tiện, kèm các chỉ số sinh hiệu nếu tự đo được tại nhà (huyết áp, mạch, SpO₂).
  - Hệ thống tự động gửi form check-in vào khung giờ ưu tiên của bệnh nhân.
- **Check-in mốc trọng điểm (POD 1, 3, 7, 14):**
  - Tích hợp thêm các câu hỏi khảo sát và đánh giá chuyên sâu phù hợp với từng giai đoạn phục hồi.
- **Nhắc thuốc và lịch tái khám:**
  - Gửi thông báo nhắc uống thuốc hằng ngày theo đúng đơn thuốc xuất viện; bệnh nhân tương tác để xác nhận tuân thủ.
  - Gửi thông báo nhắc hẹn tái khám đúng lịch.

#### Các giai đoạn và trọng tâm theo dõi lâm sàng:
* **POD 1 - 3 (Hậu phẫu sớm):**
  - Kiểm soát và đánh giá mức độ đau sau mổ.
  - Đánh giá khả năng hồi phục nhu động ruột (sự xuất hiện của trung tiện, đại tiện).
  - Khả năng dung nạp dinh dưỡng chuyển dần từ thức ăn lỏng sang thức ăn đặc.
  - Giám sát dấu hiệu chảy máu bất thường hoặc tình trạng dịch dẫn lưu (nếu có).
* **POD 4 - 7 (Hồi phục tại nhà):**
  - Nhận diện sớm các dấu hiệu nhiễm trùng vết mổ: sưng phồng, nóng đỏ, đau tăng dần, rỉ dịch mủ hoặc chảy máu.
  - Kiểm tra tính tuân thủ đơn thuốc kháng sinh và thuốc giảm đau theo toa xuất viện.
* **POD 8 - 14 (Hồi phục ổn định):**
  - Khuyến khích tăng dần mức độ vận động thể chất nhẹ nhàng.
  - Duy trì chế độ dinh dưỡng lành mạnh giúp liền sẹo.
  - Đánh giá mức độ liền vết mổ và nhắc nhở lịch hẹn tái khám với bác sĩ phẫu thuật.

#### Quy trình xử lý không phản hồi (Missed Check-in Protocol):
- Gửi thông báo nhắc lại lần 1 $\rightarrow$ Gửi thông báo nhắc lại lần 2 $\rightarrow$ Ghi nhận trạng thái bỏ lỡ check-in.
- **Kích hoạt Escalation gửi điều dưỡng** trong các trường hợp:
  - Bệnh nhân bỏ lỡ check-in **2 ngày liên tiếp**, HOẶC
  - Bệnh nhân bỏ lỡ bất kỳ một check-in mốc trọng điểm nào (**POD 1, POD 3, hoặc POD 7**).

---

## MỤC 3: AN TOÀN VÀ RANH GIỚI BẢO VỆ (SAFETY & GUARDRAILS)

### 3.1. Hàng rào phát hiện biến chứng và Báo động đỏ (Red Flags)
Bộ quy tắc xác định (*Deterministic Safety Rules*) chạy độc lập trước LLM ở tất cả các lượt check-in. Mỗi luật có mã nhận diện (*Rule ID*) và phiên bản (*Version*) để phục vụ kiểm toán và truy vết.

#### Các dấu hiệu nguy cấp toàn thân:
- **Sốc / Suy tuần hoàn:** Huyết áp tâm thu < 90 mmHg, mạch > 120 lần/phút, chóng mặt dữ dội, ngất xỉu.
- **Suy hô hấp cấp:** Khó thở dữ dội, nhịp thở > 25 lần/phút, SpO₂ < 92%.
- **Biến chứng vết mổ:** Bung mép chỉ, toác vết mổ, chảy máu ồ ạt không cầm.
- **Tắc ruột cơ học / Liệt ruột:** Nôn ói liên tục kèm theo chướng bụng, bí hoàn toàn cả trung tiện và đại tiện.

#### Cờ đỏ chuyên biệt theo loại phẫu thuật:
- **Sau phẫu thuật cắt túi mật (Cholecystectomy):** 
  - *Nghi ngờ rò dịch mật hoặc tổn thương đường mật:* Đau quặn dữ dội vùng hạ sườn phải, xuất hiện vàng mắt hoặc vàng da tiến triển tăng dần, sốt cao kèm rét run.
- **Sau phẫu thuật cắt ruột thừa (Appendectomy):** 
  - *Nghi ngờ áp-xe tồn lưu hoặc nhiễm trùng trong ổ bụng:* Sốt cao kéo dài hoặc sốt tái phát sau khi đã hạ, đau hố chậu phải có xu hướng tăng dần. *(Nội dung quy tắc cần được đối chiếu chuẩn hóa từ các nguồn tài liệu y khoa công khai chính thống trước khi cấu hình vào Engine)*.

#### Quy trình xử lý ngay khi phát hiện Cờ Đỏ (RED Flag):
1. **Ngắt lập tức** luồng trò chuyện / tư vấn thông thường của AI.
2. **Tự động sinh bản nháp báo cáo lâm sàng** tổng hợp diễn biến triệu chứng và chỉ số sinh hiệu bất thường.
3. **Tạo ticket Escalation mức ưu tiên cao nhất** đẩy thẳng lên dashboard trực ban của điều dưỡng.
4. **Hiển thị chỉ dẫn khẩn cấp cho bệnh nhân:** Yêu cầu bệnh nhân gọi ngay cấp cứu 115 hoặc di chuyển đến cơ sở y tế gần nhất lập tức.

---

### 3.2. Ranh giới an toàn y tế (Safety Boundaries)

#### Các giới hạn KHÔNG ĐƯỢC LÀM:
- **Không thực hiện chẩn đoán bệnh:** Tuyệt đối không đưa ra kết luận chẩn đoán bệnh tật, không kê đơn thuốc mới, không tự ý điều chỉnh liều lượng hay chỉ định ngưng thuốc ngoài đơn xuất viện đã được bác sĩ duyệt.
- **Không tự động liên lạc cấp cứu 115:** Hệ thống không tích hợp tự động quay số hay điều phối đội cấp cứu ngoại viện; trách nhiệm của hệ thống là cảnh báo mức độ nguy hiểm và hướng dẫn bệnh nhân / người nhà chủ động gọi 115 hoặc tới viện.
- **Không kết nối trực tiếp hệ thống EMR/HIS bệnh viện thật:** Không can thiệp vào cơ sở dữ liệu bệnh án nội trú, không thay thế nhiệm vụ chuyên môn của bác sĩ phụ trách.

#### Các nguyên tắc bắt buộc:
- **Rule before model:** Luật an toàn chạy hoàn toàn độc lập với mô hình ngôn ngữ lớn (LLM). LLM không có quyền và không thể ghi đè/hạ mức độ cảnh báo từ **RED** xuống **YELLOW** hay **GREEN**.
- **Human-in-the-loop:** Chỉ có điều dưỡng hoặc nhân viên y tế có chuyên môn mới có quyền đóng (*close/resolve*) cảnh báo cờ đỏ, kèm theo ghi chú biện pháp xử lý lâm sàng bắt buộc.
- **Kế hoạch do bác sĩ phê duyệt:** Trợ lý ảo AI chỉ bám sát và hoạt động trong phạm vi kế hoạch chăm sóc xuất viện đã được duyệt, không tự ý nới lỏng hay thay đổi.
- **Grounded và chống ảo giác (Anti-hallucination):** Toàn bộ câu trả lời tư vấn chăm sóc phải được tham chiếu chặt chẽ từ tài liệu chăm sóc y tế chính thống, luôn đính kèm trích dẫn nguồn.
- **Dữ liệu mô phỏng trong giai đoạn thử nghiệm:** Trong giai đoạn MVP, hệ thống vận hành hoàn toàn trên tập dữ liệu mô phỏng (*synthetic data*) để đảm bảo an toàn tuyệt đối.
- **Bằng chứng Guardrail (Audit Trail):** Mọi lượt kích hoạt luật cờ đỏ, quy tắc an toàn hoặc vi phạm guardrails đều phải được ghi lại nhật ký (*audit log*) đầy đủ để kiểm tra và chứng minh tính toàn vẹn của hệ thống.
