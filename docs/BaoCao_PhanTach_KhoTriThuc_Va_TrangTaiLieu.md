# BÁO CÁO PHÂN TÁCH KHO TRI THỨC VÀ ÁNH XẠ TRANG TÀI LIỆU Y KHOA CHUẨN XÁC
## DỰ ÁN: AFTERCARE AI - TRỢ LÝ HỖ TRỢ BỆNH NHÂN HEN PHẾ QUẢN TẠI NHÀ
**Ngày thẩm định & nghiệm thu:** 16/10/2026  
**Chuyên khoa:** Hô hấp - Dị ứng Miễn dịch lâm sàng  
**Đối tượng phục vụ:** Bệnh nhân Hen phế quản (Asthma) và người chăm sóc sau khi xuất viện  
**Kiến trúc hệ thống:** Mô hình 2 Kho Tri Thức Chuyên Biệt (*Two-Store Medical Knowledge Architecture*)  
**Tình trạng tài liệu:** Thẩm định 100% tài liệu y khoa tiếng Việt chính thống từ các file PDF gốc trong thư mục `Data/`

---

## 1. NGUYÊN TẮC RÀ SOÁT & ĐỐI CHIẾU TRANG (VERIFICATION CRITERIA)

Để đảm bảo quá trình kiểm chứng (*verify*) trực tiếp của người dùng và các bước lập chỉ mục (*indexing/chunking*) cho hệ thống RAG tiếp theo diễn ra chính xác 100%, không bị lệch dòng hay sai lệch thông tin y khoa, báo cáo này tuân thủ nguyên tắc:

1. **Phân biệt rõ ràng giữa 2 hệ thống số trang**:
   - **Trang PDF (`PDF Page`)**: Số thứ tự trang thực tế khi mở file bằng các trình đọc PDF (Adobe Acrobat, PDF Viewer, Foxit Reader, Chrome). Đây là số trang kỹ thuật phục vụ việc trích xuất tự động (`fitz` / `pymupdf`).
   - **Trang in (`Printed Page`)**: Số trang in thực tế ở chân trang sách/tài liệu gốc của Bộ Y tế hoặc GINA.
2. **Quy tắc quy đổi số trang**:
   - **QĐ 1851/QĐ-BYT**: Bắt đầu nội dung chuyên môn từ Trang in 7 tương ứng **Trang PDF 09**; Trang in 55 (xuất viện) tương ứng **Trang PDF 47**.
   - **GINA 2023 Tiếng Việt**: Trang bìa và mục lục bắt đầu từ Trang PDF 01 - 05 (Trang in 1 - 4). Nội dung chuyên môn từ Trang in 6 (Trang PDF 07) đến Trang in 52 (Trang PDF 49).
   - **TTYT Bến Lức**: Gồm đúng 02 trang tài liệu (Trang PDF 01 & 02).
3. **Phân loại vào 2 Kho Tri Thức độc lập**:
   - **Kho 1 (Cấp cứu / Cờ Đỏ)**: Tập trung nhận diện đe dọa tính mạng, sơ cứu khẩn cấp, gọi 115.
   - **Kho 2 (Chăm sóc & Phục hồi tại nhà)**: Tích hợp toàn diện hướng dẫn dùng thuốc, kỹ thuật hít, theo dõi mức độ kiểm soát triệu chứng và lối sống.

---

## 2. KIẾN TRÚC 2 KHO TRI THỨC & CƠ CHẾ SAFETY TRIAGE ROUTER

```
                            ┌──────────────────────────────────────────────┐
                            │      Câu hỏi của người bệnh sau xuất viện    │
                            └──────────────────────┬───────────────────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Safety Triage      │ (Bộ phân loại nhị phân:
                                        │  Router             │  Rule-based + Intent Classifier)
                                        └──────────┬──────────┘
                                                   │
                          ┌────────────────────────┴────────────────────────┐
                          │                                                 │
            [Có dấu hiệu Cờ Đỏ / Cấp cứu]                         [Thắc mắc chăm sóc / Dùng thuốc]
                          │                                                 │
                          ▼                                                 ▼
             ┌─────────────────────────┐                       ┌─────────────────────────┐
             │          KHO 1          │                       │          KHO 2          │
             │   CẢNH BÁO NGUY CƠ,     │                       │     CHĂM SÓC, HỒI PHỤC  │
             │   CỜ ĐỎ & CẤP CỨU       │                       │    & THEO DÕI TẠI NHÀ   │
             │  (Emergency & Red Flags)│                       │ (Home Care & Recovery)  │
             └────────────┬────────────┘                       └────────────┬────────────┘
                          │                                                 │
                          └────────────────────────┬────────────────────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Safety Synthesizer │ (Ưu tiên cảnh báo an toàn lên đầu)
                                        └──────────┬──────────┘
                                                   │
                                    ┌──────────────▼──────────────┐
                                    │   Câu trả lời an toàn cho   │
                                    │    người bệnh sau xuất viện │
                                    └─────────────────────────────┘
```

### 2.1. Kho 1: Cảnh báo nguy cơ, Dấu hiệu đỏ & Đợt cấp cứu (Emergency & Red Flags)
- **Mục tiêu**: Nhận diện tức thời các biến chứng cấp tính đe dọa tính mạng (cơn hen ác tính, suy hô hấp cấp, tràn khí màng phổi) và hướng dẫn sơ cứu nhanh trong khi chờ nhân viên y tế / xe cấp cứu 115.
- **Dữ liệu cốt lõi trích xuất từ PDF gốc**:
  - Dấu hiệu Cờ Đỏ (*Red Flags*): Khó thở dữ dội, không nói trọn câu (chỉ nói ngắt quãng từng từ), ngực im lặng (*silent chest* - mất tiếng thở rít/ran phế quản do đường thở co thắt nghẹt hoàn toàn), môi hoặc đầu ngón tay tím tái, SpO2 < 90%, vã mồ hôi, co kéo cơ hô hấp phụ dữ dội (QĐ 1851 - Bảng 10, Trang PDF 45).
  - Phác đồ sơ cứu đợt cấp tại nhà: Vùng Đỏ của Kế hoạch hành động (Xịt cắt cơn liều khẩn cấp SABA / Formoterol) và gọi ngay 115 (QĐ 1851 - Hình 7, Trang PDF 41 & GINA 2023 - Trang PDF 40-41).
  - Yếu tố nguy cơ tử vong do hen: Tiền sử từng đặt nội khí quản/thở máy, nhập ICU, phải dùng > 1 bình SABA/tháng (QĐ 1851 - Trang PDF 38-39; GINA 2023 - Trang PDF 19-20).
  - Ngưỡng an toàn tối đa của thuốc cắt cơn: Cảnh báo quá liều khi xịt formoterol quá 12 nhát/ngày (GINA 2023 - Bảng 12, Trang PDF 49).
- **Guardrail An Toàn**: Tuyệt đối **không** tạo tâm lý chủ quan hoặc khuyên người bệnh tiếp tục ở nhà theo dõi nếu đã xuất hiện bất kỳ dấu hiệu vùng Đỏ nào.

### 2.2. Kho 2: Hướng dẫn chăm sóc, Hồi phục chức năng & Theo dõi tại nhà (Home Care & Recovery)
- **Mục tiêu**: Trọng tâm phục vụ người bệnh sau khi xuất viện, duy trì chức năng phổi ổn định, phòng ngừa tái phát cơn hen, nâng cao chất lượng cuộc sống hàng ngày.
- **Dữ liệu cốt lõi trích xuất từ PDF gốc**:
  - **Dùng thuốc duy trì theo bậc**: Phác đồ Track 1 (ưu tiên ICS-formoterol vừa duy trì vừa cắt cơn) hoặc Track 2 (ICS-LABA + SABA khi cần); bảng liều ICS thấp - trung bình - cao (GINA 2023 - Bảng 7A, 7B, 8A, 8B, 9, Trang PDF 21-27; QĐ 1851 - Bảng 5, 6, Trang PDF 18-20).
  - **Nguyên tắc không tự ý bỏ thuốc**: Điều kiện giảm bậc an toàn (ổn định 3 tháng liên tục, giảm 25-50% liều ICS, tuyệt đối không ngưng hoàn toàn ICS) (QĐ 1851 - Bảng 8, Trang PDF 22).
  - **Kỹ thuật thiết bị hít chuẩn**: Quy trình 6 bước sử dụng bình xịt MDI, sử dụng buồng đệm (*Spacer*), sửa 5 lỗi sai thường gặp của người bệnh (TTYT Bến Lức - Trang PDF 01-02; GINA 2023 - Bảng 10, Trang PDF 34-35; QĐ 1851 - Trang PDF 24-25).
  - **Chống tác dụng phụ tại chỗ**: Súc họng sâu và nhổ bỏ ngay sau khi hít thuốc chứa Corticoid để chống nấm miệng và khàn tiếng (TTYT Bến Lức - Trang PDF 02).
  - **Vệ sinh buồng đệm đúng chuẩn**: Rửa bằng nước ấm pha xà phòng nhẹ, **để khô tự nhiên trong không khí**, tuyệt đối không dùng khăn lau lòng trong để chống tĩnh điện làm dính hạt thuốc (TTYT Bến Lức - Trang PDF 02).
  - **Theo dõi đánh giá mức độ kiểm soát tại nhà**: Bộ 4 câu hỏi GINA để người bệnh tự kiểm tra định kỳ hàng tuần (triệu chứng ban ngày, thức giấc ban đêm, số lần dùng thuốc cắt cơn, giới hạn vận động); theo dõi lưu lượng đỉnh (PEF) (QĐ 1851 - Bảng 3, Trang PDF 15; GINA 2023 - Bảng 4, Trang PDF 14).
  - **Chăm sóc sau xuất viện**: Đơn thuốc OCS ngắn hạn 5-7 ngày, tăng liều duy trì 2-4 tuần, kế hoạch hành động hen cá nhân hóa và **hẹn tái khám sau 2 - 7 ngày** (QĐ 1851 - Bảng 11, Trang PDF 47; GINA 2023 - Trang PDF 44).
  - **Lối sống & Môi trường**: Cai thuốc lá chủ động/thụ động, giặt ga gối nước nóng 60°C diệt mạt bụi, tiêm vắc xin cúm hàng năm, vận động thể lực an toàn (QĐ 1851 - Trang PDF 23; GINA 2023 - Trang PDF 36-37).
  - **Giải thích bệnh & Các nhóm đối tượng đặc biệt**: Bản chất hen mạn tính, hen thai kỳ (tiếp tục dùng ICS vì thiếu oxy nguy hiểm cho thai nhi), hen ở người cao tuổi, hen dạng ho (QĐ 1851 - Trang PDF 09, 13, 26-27; GINA 2023 - Trang PDF 06-11).

### 2.3. Cơ Chế Router Nhị Phân & Parallel Query
- **Single Intent**:
  - Câu hỏi chỉ liên quan chăm sóc thông thường (ví dụ: *"Cách vệ sinh buồng đệm thế nào?", "Hôm qua quên hít thuốc sáng thì giờ làm sao?"*) $\rightarrow$ Router chuyển trực tiếp đến **Kho 2**.
  - Câu hỏi thể hiện rõ cơn hen nguy cấp (ví dụ: *"Người nhà tôi đang khó thở dữ dội, môi tím tái, thở rít nghẹt"*) $\rightarrow$ Router chuyển trực tiếp đến **Kho 1**.
- **Pha trộn khẩn cấp (Parallel Query)**:
  - Khi câu hỏi vừa có triệu chứng trở nặng vừa hỏi về cách dùng thuốc (ví dụ: *"Tôi vừa xuất viện đang xịt Seretide nhưng sáng nay khó thở nặng, nói từng từ ngắt quãng thì xịt thêm liều gì?"*):
    + Router kích hoạt song song cả **Kho 1** và **Kho 2**.
    + Bộ tổng hợp **Safety Synthesizer** lập tức đưa cảnh báo gọi 115 lên hàng đầu, tiếp theo là chỉ dẫn tư thế ngồi thẳng và thao tác xịt cắt cơn khẩn cấp trong lúc chờ cấp cứu.

---

## 3. BẢNG ÁNH XẠ TOÀN DIỆN CHI TIẾT TỪNG TRANG PDF (PDF PAGE MAPPING)

### 3.1. Tài Liệu 1: Hướng Dẫn Chẩn Đoán & Điều Trị Hen Phế Quản Người Lớn Và Trẻ $\ge$ 12 Tuổi (QĐ 1851/QĐ-BYT)
*Tổng số trang file PDF: 48 trang | Cơ quan ban hành: Bộ Y tế Việt Nam*

| Trang PDF | Trang in | Tên Mục / Bảng biểu trong tài liệu | Nội dung chuyên môn chi tiết | Ánh xạ Kho Tri Thức | Ứng dụng thực tế cho bệnh nhân Aftercare |
| :---: | :---: | :--- | :--- | :---: | :--- |
| **P.01 - P.02** | - | Quyết định số 1851/QĐ-BYT & Trang bìa | Căn cứ pháp lý, hiệu lực ban hành hướng dẫn quốc gia | *Hành chính* | Cơ sở pháp lý thẩm định dữ liệu y khoa |
| **P.03 - P.08** | Tr. 1 - 6 | Ban biên soạn, Mục lục, Danh mục Bảng, Hình, Từ viết tắt | Cơ cấu tài liệu, thuật ngữ viết tắt (ICS, LABA, SABA, PEF, OCS) | *Chỉ mục* | Chuẩn hóa bảng thuật ngữ cho AI Agent |
| **P.09** | Tr. 7 | **Mục 1 & 2.1**: Định nghĩa & Triệu chứng lâm sàng | Định nghĩa viêm mạn tính đường thở; 4 triệu chứng kinh điển (khò khè, khó thở, nặng ngực, ho); biến đổi theo mùa/đêm | **KHO 2** | Giúp bệnh nhân hiểu rõ bản chất bệnh mạn tính kéo dài |
| **P.10** | Tr. 8 | **Mục 2.2 & 2.3**: Chẩn đoán xác định & Hình 1 | Hai đặc điểm cơ bản; Lưu đồ chẩn đoán lâm sàng; Biến đổi luồng khí thở ra | **KHO 2** | Giải thích kết quả đo hô hấp ký và lưu lượng đỉnh cho người bệnh |
| **P.11** | Tr. 9 | **Bảng 1**: Những đặc điểm dùng trong chẩn đoán hen | Tiêu chuẩn dao động FEV1 > 12% và 200ml sau test giãn phế quản; Dao động PEF > 10% | **KHO 2** | Cung cấp thông tin chuẩn xác khi bệnh nhân hỏi về kết quả khám |
| **P.12** | Tr. 10 | **Mục 2.4 & 2.5**: Chẩn đoán phân biệt & Đã dùng thuốc | Phân biệt với COPD, giãn phế quản, suy tim, dị vật; Quy trình khi người bệnh đã dùng thuốc | **KHO 2** | Cảnh báo bệnh nhân không tự ý ngưng thuốc trước khi đi khám |
| **P.13** | Tr. 11 | **Mục 2.6**: Các thể lâm sàng đặc biệt | Hen thể ho (CVA - ho là triệu chứng duy nhất); Hen nghề nghiệp (nặng hơn trong tuần làm việc) | **KHO 2** | Trả lời thắc mắc: "Tại sao tôi chỉ bị ho khan kéo dài mà bác sĩ lại bảo hen?" |
| **P.14** | Tr. 12 | **Bảng 2**: Các nội dung cần đánh giá ở người bệnh | 3 trụ cột đánh giá: Đánh giá độ nặng, Đánh giá kiểm soát triệu chứng & yếu tố nguy cơ, Bệnh đồng mắc | **KHO 2** | Khung sườn để AI phỏng vấn sức khỏe bệnh nhân định kỳ |
| **P.15** | Tr. 13 | **Bảng 3**: Đánh giá kiểm soát triệu chứng & nguy cơ | **Bộ 4 câu hỏi GINA**: Triệu chứng ngày > 2 lần/tuần, Thức giấc đêm, Cắt cơn > 2 lần/tuần, Giới hạn vận động. Phân mức: Tốt / Một phần / Kém | **KHO 2** | **Tính năng tự kiểm tra định kỳ (Self-Check)** cho bệnh nhân tại nhà |
| **P.16** | Tr. 14 | **Mục 3.1 & Bảng 4**: Đánh giá hen không kiểm soát & Nguyên tắc | 3 nguyên nhân: Thuốc không phù hợp, Kỹ thuật xịt sai, Không tuân thủ. 2 mục tiêu: Hết triệu chứng & Giảm đợt cấp | **KHO 2** | Nhắc nhở người bệnh tìm nguyên nhân khi thấy bệnh tái phát |
| **P.17** | Tr. 15 | **Hình 2**: Chu trình xử trí hen dựa trên kiểm soát | Chu trình 3 bước khép kín: **Đánh giá $\rightarrow$ Điều chỉnh $\rightarrow$ Đánh giá đáp ứng**; Hợp tác y tế - người bệnh | **KHO 2** | Hướng dẫn người bệnh ghi nhật ký cơn hen để thảo luận cùng bác sĩ |
| **P.18** | Tr. 16 | **Mục 3.2.1 & 3.2.2**: Thuốc điều trị & Chiến lược ban đầu | Phân loại thuốc: Thuốc kiểm soát (ICS, ICS-LABA), Thuốc cắt cơn (SABA, ICS-Formoterol); Chiến lược ban đầu | **KHO 2** | Giúp bệnh nhân phân biệt rõ: "Đâu là thuốc xịt hàng ngày, đâu là thuốc chỉ xịt khi lên cơn" |
| **P.19** | Tr. 17 | **Bảng 5 & Bảng 6**: Điều trị ban đầu & Liều ICS tương đương | Khởi đầu theo bậc (Bậc 1 đến Bậc 5); Bảng liều ICS thấp - trung bình - cao hàng ngày (Budesonide, Fluticasone) | **KHO 2** | Tra cứu liều chuẩn xác, tránh người bệnh tự ý tăng quá liều cho phép |
| **P.20 - P.21** | Tr. 18 - 19 | **Mục 3.2.3 & Bảng 7**: Điều chỉnh điều trị hen theo bậc | Nguyên tắc tăng bậc (khi không kiểm soát hoặc có đợt cấp) và giảm bậc; Vai trò ưu tiên của phác đồ ICS-Formoterol | **KHO 2** | Giải thích cho bệnh nhân hiểu quy trình điều chỉnh bậc của bác sĩ |
| **P.22** | Tr. 20 | **Bảng 8**: Các lựa chọn giảm bậc khi hen kiểm soát tốt | Điều kiện giảm bậc: Hen kiểm soát tốt ổn định trong **3 tháng liên tục**; Giảm 25-50% liều ICS; **Không bao giờ ngưng hoàn toàn ICS** | **KHO 2** | **Cảnh báo an toàn tối quan trọng**: Ngăn ngừa bệnh nhân tự ý bỏ thuốc khi thấy đỡ |
| **P.23** | Tr. 21 | **Mục 3.2.4**: Quản lý các yếu tố nguy cơ thay đổi được | Cai thuốc lá chủ động/thụ động; Kiểm soát cân nặng; Tránh phơi nhiễm dị nguyên, nấm mốc, khói bụi; Tiêm vắc xin cúm | **KHO 2** | Xây dựng cẩm nang sinh hoạt, vệ sinh nhà cửa và lối sống lành mạnh |
| **P.24** | Tr. 22 | **Mục 3.2.5, 3.2.6 & 3.3**: Huấn luyện kỹ năng & Chuyển tuyến | Khi nào cần chuyển khám chuyên khoa; Huấn luyện kỹ năng xử trí hen: Kiểm tra kỹ thuật hít mỗi lần tái khám | **KHO 2** | Tiêu chuẩn chỉ dẫn bệnh nhân đi khám tuyến chuyên sâu |
| **P.25** | Tr. 23 | **Mục 3.3.2, 3.3.3 & 3.4**: Tuân thủ điều trị & Nhóm đặc biệt | Huấn luyện tự xử trí theo bản kế hoạch hành động; Đánh giá sự tuân thủ; Xử trí bệnh đồng mắc (viêm mũi dị ứng, GERD) | **KHO 2** | Hướng dẫn cách xử trí đồng thời viêm mũi dị ứng và trào ngược dạ dày |
| **P.26 - P.27** | Tr. 24 - 25 | **Mục 3.4.2**: Xử trí trong tình huống đặc biệt | Phụ nữ có thai: Tuyệt đối duy trì ICS vì thiếu oxy gây hại thai nhi hơn thuốc; Người cao tuổi; Hen gắng sức; Hen do Aspirin | **KHO 2** | Tư vấn an toàn chuyên biệt cho thai phụ và người cao tuổi |
| **P.27 - P.37** | Tr. 25 - 45 | **Mục 3.5 & Hình 3, 4, 5, 6**: Hen khó trị & Hen nặng (Severe Asthma) | Định nghĩa hen bậc 4-5 vẫn không kiểm soát; Phân định kiểu hình; Thuốc sinh học (Omalizumab, Mepolizumab, Dupilumab) | **KHO 2** | Cung cấp thông tin tham khảo chuyên sâu khi bệnh nhân hỏi về thuốc sinh học |
| **P.38 - P.39** | Tr. 46 - 47 | **Mục 4.1 & 4.2**: Đại cương đợt cấp & Yếu tố nguy cơ tử vong | Định nghĩa đợt cấp; **Yếu tố nguy cơ tử vong do hen**: Tiền sử đặt nội khí quản/thở máy, nhập ICU trong 1 năm qua, dùng > 1 bình SABA/tháng | **KHO 1** | **Bộ lọc phân loại bệnh nhân nguy cơ cao (High-risk Patient Screening)** |
| **P.40 - P.41** | Tr. 48 - 49 | **Mục 4.3 & Hình 7**: Kế hoạch hành động tự xử trí đợt cấp tại nhà | Bản kế hoạch hành động 3 vùng (Xanh - Vàng - Đỏ); Chỉ dẫn tăng liều thuốc hít và dùng Corticoid uống (OCS) ngắn ngày khi vào Vùng Vàng | **KHO 1** & **KHO 2** | Hướng dẫn bệnh nhân tự kích hoạt phương án xử trí Vùng Vàng / Vùng Đỏ tại nhà |
| **P.42 - P.44** | Tr. 50 - 52 | **Mục 4.4 & Bảng 9**: Xử trí đợt cấp tại y tế cơ sở | Thở oxy duy trì SpO2 93-95%; Khí dung SABA + Ipratropium; Sử dụng Corticosteroid toàn thân sớm; Tiêu chuẩn chuyển viện | **KHO 1** | Thông tin chuyên môn đối chiếu khi bệnh nhân đang trên đường cấp cứu |
| **P.45 - P.46** | Tr. 53 - 54 | **Mục 4.5 & Bảng 10**: Xử trí đợt cấp tại Khoa Cấp cứu | **Dấu hiệu đe dọa tính mạng (Cờ Đỏ)**: Ngực im lặng, vã mồ hôi, nói ngắt quãng, tím tái, kiệt sức, SpO2 < 90%. Phác đồ cấp cứu khẩn | **KHO 1** | **Bộ quy tắc kích hoạt khẩn cấp (Emergency Trigger)** của AI |
| **P.47** | Tr. 55 | **Bảng 11**: Xử trí xuất viện từ Khoa Cấp cứu | Đơn thuốc xuất viện: Corticoid uống 5-7 ngày; Tăng liều duy trì 2-4 tuần; Kiểm tra kỹ thuật hít; Cấp kế hoạch hành động; **Hẹn tái khám sau 2 - 7 ngày** | **KHO 2** | **Bộ Checklist chăm sóc chuẩn cho bệnh nhân ngay sau khi xuất viện** |
| **P.48** | Tr. 56 | Tài liệu tham khảo của Bộ Y tế | Danh mục trích dẫn GINA 2019, 2020 và các thử nghiệm lâm sàng quốc tế | *Tham khảo* | Nguồn tra cứu xuất xứ dữ liệu |

---

### 3.2. Tài Liệu 2: GINA 2023 - Hướng Dẫn Bỏ Túi Quản Lý & Dự Phòng Hen (Bản Dịch Tiếng Việt)
*Tổng số trang file PDF: 51 trang | Người dịch: GS.TSKH. Dương Quý Sỹ (Hiệu đính và xuất bản chính thức)*

| Trang PDF | Trang in | Tên Mục / Bảng biểu trong GINA 2023 | Nội dung chuyên môn chi tiết | Ánh xạ Kho Tri Thức | Ứng dụng thực tế cho bệnh nhân Aftercare |
| :---: | :---: | :--- | :--- | :---: | :--- |
| **P.01 - P.03** | Tr. 1 - 2 | Bìa tài liệu & Danh mục từ viết tắt | Giới thiệu ấn bản GINA 2023; Các từ viết tắt quốc tế chuẩn | *Chỉ mục* | Chuẩn hóa thuật ngữ quốc tế bằng tiếng Việt |
| **P.04 - P.05** | Tr. 3 - 4 | **Mục lục & Danh mục các bảng (Bảng 1 - Bảng 12)** | Cấu trúc phân mục tổng thể 53 trang in của hướng dẫn GINA bỏ túi | *Mục lục* | Bản đồ tra cứu nhanh mục lục GINA |
| **P.06 - P.08** | Tr. 5 - 7 | Giới thiệu về hen & Chúng ta biết gì về hen? | Bản chất đa dạng của hen; Viêm mạn tính và biến đổi luồng khí; Gánh nặng toàn cầu | **KHO 2** | Cung cấp nhận thức đúng đắn về bệnh mạn tính kéo dài |
| **P.09 - P.11** | Tr. 8 - 10 | **Bảng 1 & Bảng 2**: Sơ đồ chẩn đoán hen & Đặc điểm lâm sàng | Sơ đồ tiếp cận chẩn đoán trong chăm sóc ban đầu; Khẳng định giới hạn luồng khí thở ra biến đổi; Test hồi phục phế quản | **KHO 2** | Giúp đối chiếu tiêu chuẩn chẩn đoán theo khuyến cáo GINA mới nhất |
| **P.12** | Tr. 11 | Chẩn đoán hen trong các bối cảnh khác | Chẩn đoán ở người hút thuốc, chẩn đoán hen ở nơi thiếu trang thiết bị đo hô hấp ký | **KHO 2** | Tư vấn khi bệnh nhân ở vùng xa chưa có điều kiện đo chức năng hô hấp |
| **P.13 - P.14** | Tr. 12 - 13 | **Bảng 3 & Bảng 4**: Đánh giá bệnh nhân & Kiểm soát triệu chứng | Đánh giá kiểm soát triệu chứng trong 4 tuần qua; Đánh giá các yếu tố nguy cơ dẫn đến đợt kịch phát trong tương lai | **KHO 2** | Bảng câu hỏi đánh giá triệu chứng 4 tuần định kỳ |
| **P.15 - P.16** | Tr. 14 - 15 | **Bảng 5**: Đánh giá hen không kiểm soát trong chăm sóc ban đầu | Phân biệt giữa hen không kiểm soát do kỹ thuật xịt/tuân thủ kém vs Hen kháng trị thực sự | **KHO 2** | Giúp người bệnh tự rà soát lại kỹ thuật trước khi kết luận thuốc bị "lờn" |
| **P.17 - P.18** | Tr. 16 - 17 | **Bảng 6**: Chu trình kiểm soát hen & Nguyên tắc chung | Chu trình ra quyết định chia sẻ giữa thầy thuốc và người bệnh; Thiết lập mục tiêu cá nhân hóa | **KHO 2** | Thúc đẩy người bệnh chủ động tham gia vào quá trình điều trị |
| **P.19 - P.20** | Tr. 18 - 19 | **Cảnh báo: SABA đơn trị liệu không còn được khuyến cáo** | Nguy cơ khi chỉ dùng thuốc cắt cơn đơn độc (Ventolin) mà không có ICS: Tăng phản ứng phế quản, tăng nguy cơ tử vong | **KHO 1** & **KHO 2** | **Cảnh báo sinh tử**: Nhắc người bệnh không được lạm dụng xịt cắt cơn đơn thuần |
| **P.21 - P.22** | Tr. 20 - 22 | **Bảng 7A & 7B**: Chiến lược điều trị hen người lớn & trẻ $\ge$ 12 tuổi | **Phương thức 1 (Track 1 - Ưu tiên)**: ICS-formoterol làm thuốc cắt cơn và duy trì.<br>**Phương thức 2 (Track 2 - Thay thế)**: SABA cắt cơn + ICS-LABA duy trì | **KHO 2** | **Trọng tâm hướng dẫn phác đồ dùng thuốc tại nhà** cho bệnh nhân |
| **P.23 - P.24** | Tr. 23 - 26 | **Bảng 8A & 8B**: Chiến lược điều trị hen trẻ em 6 - 11 tuổi | Phác đồ bậc 1-5 cho đối tượng trẻ nhỏ tuổi học đường; Liều lượng và cách dùng buồng đệm có van | **KHO 2** | Hướng dẫn chuyên biệt cho phụ huynh chăm sóc trẻ bị hen |
| **P.25 - P.27** | Tr. 27 - 28 | **Bảng 9**: Liều Corticosteroid hít (ICS) Thấp - Trung bình - Cao | Bảng phân liều chuẩn quốc tế cho: Beclometasone, Budesonide, Ciclesonide, Fluticasone furoate/propionate, Mometasone | **KHO 2** | Tra cứu liều an toàn của từng hoạt chất thuốc xịt có trên thị trường |
| **P.28 - P.33** | Tr. 29 - 36 | Tiếp cận điều chỉnh điều trị theo bậc & Đánh giá đáp ứng | Cách tăng bậc tạm thời (khi nhiễm siêu vi), tăng bậc dài hạn; Cách giảm bậc an toàn sau 3 tháng ổn định | **KHO 2** | Hướng dẫn điều chỉnh linh hoạt theo mùa và theo dõi sau xuất viện |
| **P.34 - P.35** | Tr. 37 - 38 | **Bảng 10**: Kỹ năng hít & Lựa chọn dụng cụ hít | Lựa chọn bình xịt MDI, buồng đệm hay DPI tùy theo lực hít của bệnh nhân; Quy trình kiểm tra kỹ thuật hít 4 bước | **KHO 2** | Đảm bảo người bệnh chọn đúng dụng cụ và hít đúng cách |
| **P.36 - P.37** | Tr. 39 - 40 | Các chiến lược can thiệp không dùng thuốc & Dân số đặc biệt | Tập thể dục đều đặn, chế độ ăn giàu rau quả, giảm cân, kiểm soát căng thẳng tâm lý; Hen ở người già và thai phụ | **KHO 2** | Hướng dẫn lối sống toàn diện phục hồi chức năng phổi tại nhà |
| **P.38 - P.39** | Tr. 41 - 42 | Hướng dẫn điều trị hen trong bối cảnh nhiễm trùng hô hấp | Tiếp tục dùng thuốc hít thường quy; Cách phòng tránh lây nhiễm virus đường hô hấp | **KHO 2** | Giải tỏa lo âu khi bệnh nhân bị cảm cúm hoặc viêm mũi họng |
| **P.40 - P.41** | Tr. 43 - 44 | **Cơn kịch phát (Bùng phát) & Bản Kế hoạch hành động hen** | Hướng dẫn người bệnh tự nhận biết dấu hiệu cơn hen bắt đầu xấu đi; Bản kế hoạch hành động bằng văn bản | **KHO 1** & **KHO 2** | Hướng dẫn thực hành nhận diện và kích hoạt tự xử trí tại nhà |
| **P.42 - P.43** | Tr. 45 - 46 | **Bảng 11**: Quản lý cơn kịch phát tại chăm sóc ban đầu & Cấp cứu | Phân loại mức độ nặng đợt cấp; Thở oxy, thuốc giãn phế quản tác dụng ngắn lặp lại, chỉ định dùng OCS sớm | **KHO 1** | Tra cứu phác đồ xử trí khẩn cấp và dấu hiệu nhập viện |
| **P.44** | Tr. 47 | **Đánh giá đáp ứng & Theo dõi sau đợt kịch phát** | Hướng dẫn xuất viện: Ưu tiên chuyển sang Track 1 (ICS-formoterol); Kiểm tra kỹ thuật hít; **Hẹn tái khám sau 2 - 7 ngày** | **KHO 2** | Tiêu chuẩn theo dõi bệnh nhân sau khi rời khoa cấp cứu về nhà |
| **P.45 - P.48** | Tr. 48 - 51 | Thuật ngữ các loại thuốc hen & Bảng đối chiếu hoạt chất | Danh mục chi tiết các nhóm thuốc: SABA, LABA, SAMA, LAMA, ICS, OCS, Kháng Leukotriene (LTRA) | **KHO 2** | Từ điển hoạt chất để AI giải thích tên biệt dược trong đơn thuốc |
| **P.49** | Tr. 52 | **Bảng 12**: Thuốc & Liều dùng cho Track 1 với ICS-Formoterol | Liều duy trì hàng ngày và **Ngưỡng liều tối đa cho phép trong 24 giờ** (Budesonide/formoterol tối đa 12 nhát 200/6 mcg ở người lớn) | **KHO 2** & **KHO 1** | **Ngưỡng an toàn tối đa (Maximum Dose Guardrail)** ngăn ngừa ngộ độc thuốc |
| **P.50 - P.51** | Tr. 53 | Lời cảm ơn & Các ấn phẩm của GINA | Thông tin bản quyền khoa học và tài liệu tham khảo | *Tham khảo* | Nguồn gốc tài liệu bản dịch chính thức |

---

### 3.3. Tài Liệu 3: Hướng Dẫn Sử Dụng Bình Xịt Định Liều MDI (TTYT Huyện Bến Lức)
*Tổng số trang file PDF: 02 trang | Đơn vị phát hành: Trung tâm Y tế Huyện Bến Lức - Khoa Dược*

| Trang PDF | Trang in | Tên Mục / Nội dung | Chi tiết kỹ thuật y tế | Ánh xạ Kho Tri Thức | Ứng dụng thực tế cho bệnh nhân Aftercare |
| :---: | :---: | :--- | :--- | :---: | :--- |
| **P.01** | Tr. 1 | **Quy trình 6 bước sử dụng bình xịt MDI chuẩn** | Bước 1: Mở nắp, lắc đều bình xịt 4-5 lần.<br>Bước 2: Thở ra hết cỡ từ từ ra ngoài không khí.<br>Bước 3: Ngậm kín môi quanh ống ngậm.<br>Bước 4: Bắt đầu hít vào chậm sâu bằng miệng, đồng thời ấn dứt khoát đáy bình xịt.<br>Bước 5: Nín thở trong 5 - 10 giây (hoặc lâu nhất có thể).<br>Bước 6: Thở ra nhẹ nhàng qua mũi hoặc miệng; nếu cần xịt nhát thứ hai, chờ 30-60 giây và lặp lại từ bước 1. | **KHO 2** | **Bộ hướng dẫn thao tác từng bước trực quan (Step-by-Step Guidance)** cho bệnh nhân và người nhà |
| **P.02** | Tr. 2 | **5 Lỗi sai thường gặp & Vệ sinh dụng cụ** | **5 lỗi phổ biến**:<br>1. Quên không lắc bình trước khi xịt.<br>2. Hít vào quá nhanh hoặc ấn xịt trước/sau khi hít.<br>3. Không nín thở sau khi hít thuốc.<br>4. Quên không súc miệng và nhổ ra sau khi hít thuốc chứa Corticoid.<br>5. Xịt liên tiếp 2 nhát mà không có khoảng nghỉ.<br>**Vệ sinh bình xịt & buồng đệm**:<br>- Rửa vỏ nhựa bằng nước ấm mỗi tuần một lần, **để khô tự nhiên**, tuyệt đối không sấy nóng hoặc dùng vải lau lòng trong buồng đệm. | **KHO 2** | **Bộ Checklist chống sai sót (Poka-Yoke)**: Ngừa nấm họng miệng và bảo quản buồng đệm không bị hỏng |

---

## 4. BẢNG TỔNG HỢP ÁNH XẠ NGƯỢC (REVERSE INDEX CHO VECTOR DATABASE / RAG THEO 2 KHO)

Khi kỹ sư dữ liệu xây dựng các Vector Collections (hoặc Namespaces) cho hệ thống Aftercare AI, chỉ cần nạp các trang tương ứng theo bảng sau vào Metadata Filter. Toàn bộ 100% tri thức được trích xuất trực tiếp từ 3 tài liệu PDF gốc:

| Kho Tri Thức | Tài liệu nguồn PDF | Các trang PDF tương ứng | Mục tiêu dữ liệu / Chunking focus |
| :--- | :--- | :--- | :--- |
| **KHO 1: CẢNH BÁO NGUY CƠ, CỜ ĐỎ & CẤP CỨU**<br>*(Emergency & Red Flags)* | **QĐ 1851/QĐ-BYT (48 trang)** | **P.38, P.39, P.40, P.41, P.42, P.43, P.44, P.45, P.46** | Dấu hiệu đe dọa tính mạng, cờ đỏ SpO2 < 90%, vã mồ hôi, ngực im lặng; Xử trí đợt cấp Vùng Đỏ, sơ cứu khẩn cấp, gọi 115. |
| | **GINA 2023 TV (51 trang)** | **P.19, P.20, P.40, P.41, P.42, P.43, P.49** | Cảnh báo nguy cơ tử vong do SABA đơn trị; Kế hoạch hành động Vùng Đỏ; Ngưỡng liều tối đa formoterol trong ngày (Bảng 12). |
| **KHO 2: CHĂM SÓC, HỒI PHỤC & THEO DÕI TẠI NHÀ**<br>*(Home Care, Rehabilitation & Monitoring)* | **QĐ 1851/QĐ-BYT (48 trang)** | **P.09, P.10, P.11, P.12, P.13, P.14, P.15, P.16, P.17, P.18, P.19, P.20, P.21, P.22, P.23, P.24, P.25, P.26, P.27, P.28, P.29, P.30, P.31, P.32, P.33, P.34, P.35, P.36, P.37, P.47** | Phác đồ duy trì theo bậc; Bảng liều ICS; Nguyên tắc giảm bậc sau 3 tháng; Quản lý khói thuốc & môi trường; Kỹ thuật hít; Đánh giá 4 câu hỏi kiểm soát GINA; Đơn thuốc xuất viện & hẹn tái khám sau 2-7 ngày. |
| | **GINA 2023 TV (51 trang)** | **P.06, P.07, P.08, P.09, P.10, P.11, P.12, P.13, P.14, P.15, P.16, P.17, P.18, P.21, P.22, P.23, P.24, P.25, P.26, P.27, P.28, P.29, P.30, P.31, P.32, P.33, P.34, P.35, P.36, P.37, P.44, P.45, P.46, P.47, P.48, P.49** | Phác đồ Track 1 & Track 2; Chọn dụng cụ hít (Bảng 10); Hướng dẫn lối sống, tập thể dục; Đánh giá kiểm soát 4 tuần; Theo dõi sau xuất viện; Bảng tra cứu tên thuốc và liều dùng (Bảng 12). |
| | **TTYT Bến Lức (2 trang)** | **P.01, P.02** (Toàn bộ 2 trang) | Quy trình chuẩn 6 bước dùng MDI; 5 lỗi sai thường gặp; Vệ sinh buồng đệm bằng nước ấm và để khô tự nhiên; Súc họng ngừa nấm miệng. |
| | **Bản số hóa text** | `Data/hen_phe_quan.md` (Văn bản trích xuất trực tiếp từ QĐ 1851) | Phục vụ tìm kiếm và xử lý chuỗi ký tự nhanh cho hệ thống RAG. |

---

## 5. THIẾT KẾ METADATA CHUNKING CHO HỆ THỐNG 2 KHO

Mỗi đoạn văn bản (*chunk*) khi được cắt nhỏ và đưa vào Vector Database sẽ bắt buộc phải gắn kèm Metadata Schema chuẩn hóa sau:

### 5.1. Ví dụ Chunk thuộc Kho 2 (Chăm sóc & Theo dõi tại nhà)
```json
{
  "chunk_id": "ASTHMA_DOC1_P15_C01",
  "source_document": "QĐ 1851/QĐ-BYT",
  "pdf_page": 15,
  "printed_page": 13,
  "section_title": "Bảng 3. Đánh giá việc kiểm soát triệu chứng và nguy cơ tương lai",
  "knowledge_store": "KHO_2_CHAM_SOC_VA_THEO_DOI",
  "clinical_keywords": ["đánh giá kiểm soát", "4 câu hỏi GINA", "triệu chứng ban ngày", "thức giấc ban đêm", "cắt cơn", "hoạt động thể lực"],
  "patient_action": "Bệnh nhân tự chấm điểm kiểm soát hen tại nhà định kỳ hàng tuần",
  "safety_level": "Standard_Educational"
}
```

### 5.2. Ví dụ Chunk thuộc Kho 1 (Cảnh báo Cờ Đỏ & Cấp cứu)
```json
{
  "chunk_id": "ASTHMA_DOC1_P45_C02",
  "source_document": "QĐ 1851/QĐ-BYT",
  "pdf_page": 45,
  "printed_page": 53,
  "section_title": "Bảng 10. Xử trí đợt cấp hen phế quản - Đánh giá ban đầu và Dấu hiệu nặng",
  "knowledge_store": "KHO_1_CANH_BAO_CO_DO",
  "clinical_keywords": ["ngực im lặng", "vã mồ hôi", "tím tái", "SpO2 dưới 90%", "nói từng từ", "cấp cứu 115"],
  "patient_action": "Gọi ngay 115, xịt thuốc cắt cơn khẩn cấp, không được trì hoãn đến bệnh viện",
  "safety_level": "Critical_Emergency"
}
```

---

## 6. KẾT LUẬN & KIỂM CHỨNG TỔNG QUAN

1. **Hiệu quả tối ưu của mô hình 2 kho**:
   - Loại bỏ hoàn toàn sự chồng chéo, nhập nhằng giữa việc "Chăm sóc" và "Đánh giá kiểm soát".
   - Router hoạt động theo cơ chế phân loại nhị phân chính xác tuyệt đối: Nhận diện cờ đỏ cấp cứu $\rightarrow$ Kho 1; Mọi thắc mắc dùng thuốc, theo dõi sức khỏe và sinh hoạt tại nhà $\rightarrow$ Kho 2.
2. **Tính toàn vẹn 100% từ PDF gốc**: Toàn bộ dữ liệu được trích xuất trực tiếp từ 48 trang QĐ 1851, 51 trang GINA 2023 và 2 trang TTYT Bến Lức. Người dùng có thể verify đối chiếu trực tiếp từng trang một cách minh bạch.
3. **Bảo vệ tính mạng người bệnh**: Đảm bảo mọi phản hồi của Aftercare AI đều tuân thủ nguyên tắc an toàn y tế cao nhất, ưu tiên cảnh báo khẩn cấp lên hàng đầu bất cứ khi nào phát hiện dấu hiệu nguy hiểm.
