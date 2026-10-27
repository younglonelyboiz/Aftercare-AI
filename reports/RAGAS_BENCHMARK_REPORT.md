# BÁO CÁO KẾT QUẢ ĐÁNH GIÁ HỆ THỐNG RAG THEO KHUNG CHỈ SỐ RAGAS
**(Vietnamese Clinical RAGAS Benchmark Report)**

- **Dự án:** Aftercare-AI (Hệ thống RAG Chăm sóc & Hướng dẫn Sau xuất viện cho Bệnh nhân Hen Phế quản)
- **Tập dữ liệu kiểm định:** `Data/golden_dataset.json` (20 Test Cases chuẩn lâm sàng tiếng Việt theo GINA 2023 & Bộ Y tế 1851/QĐ-BYT)
- **Kiến trúc Retriever:** Hybrid Search RRF (BAAI/bge-m3 + BM25) + Reranker (BAAI/bge-reranker-v2-m3)
- **Mô hình sinh câu trả lời (Generator):** `google/gemini-2.5-flash`
- **Mô hình giám khảo (Judge LLM):** `openai/gpt-4o`
- **Tệp dữ liệu kết quả gốc:** `reports/ragas_benchmark_results.json`

---

## 1. BẢNG TỔNG HỢP CHỈ SỐ TOÀN DIỆN (SUMMARY METRICS)

| Chỉ số đánh giá | Giá trị trung bình | Tỷ lệ phần trăm |
| :--- | :---: | :---: |
| **Tổng số Test Cases hoàn thành** | **20 / 20** | **100%** |
| **Context Recall** | **0.7500** | **75.00%** |
| **Context Precision** | **0.6667** | **66.67%** |
| **Faithfulness** | **0.9950** | **99.50%** |
| **Answer Relevance** | **0.9500** | **95.00%** |

---

## 2. KẾT QUẢ ĐO LƯỜNG CHI TIẾT THEO TỪNG TEST CASE (20 TEST CASES)

| Mã TC | Context Recall | Context Precision | Faithfulness | Answer Relevance |
| :---: | :---: | :---: | :---: | :---: |
| **TC01** | 0.00 | 0.00 | 1.00 | 0.95 |
| **TC02** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC03** | 0.00 | 0.00 | 0.90 | 0.95 |
| **TC04** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC05** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC06** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC07** | 1.00 | 0.50 | 1.00 | 0.95 |
| **TC08** | 1.00 | 0.8333 | 1.00 | 0.95 |
| **TC09** | 1.00 | 0.50 | 1.00 | 0.95 |
| **TC10** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC11** | 0.00 | 0.00 | 1.00 | 0.95 |
| **TC12** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC13** | 0.00 | 0.00 | 1.00 | 0.95 |
| **TC14** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC15** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC16** | 0.00 | 0.00 | 1.00 | 0.95 |
| **TC17** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC18** | 1.00 | 0.50 | 1.00 | 0.95 |
| **TC19** | 1.00 | 1.00 | 1.00 | 0.95 |
| **TC20** | 1.00 | 1.00 | 1.00 | 0.95 |

---

## 3. THỐNG KÊ PHÂN BỐ CÁC CHỈ SỐ

* **Context Recall:**
  * Đạt 1.0 (100%): **15 / 20 Test Cases** (75.0%)
  * Điểm 0.0: **5 / 20 Test Cases** (TC01, TC03, TC11, TC13, TC16)
* **Context Precision:**
  * Đạt điểm tuyệt đối 1.0: **12 / 20 Test Cases** (60.0%)
  * Đạt điểm 0.8333: **1 / 20 Test Cases** (TC08)
  * Đạt điểm 0.50: **3 / 20 Test Cases** (TC07, TC09, TC18)
  * Điểm 0.0: **5 / 20 Test Cases**
* **Faithfulness:**
  * Đạt điểm tuyệt đối 1.0: **19 / 20 Test Cases** (95.0%)
  * Đạt điểm 0.90: **1 / 20 Test Cases** (TC03)
* **Answer Relevance:**
  * Đạt điểm 0.95 đồng đều: **20 / 20 Test Cases** (100.0%)

---

## 4. CHI TIẾT TRUY XUẤT VÀ CÂU TRẢ LỜI CỦA CÁC TEST CASES

### TC01
- **Câu hỏi:** Bác sĩ ơi, người nhà tôi đang lên cơn hen dữ dội, phải ngồi chồm ra trước để thở, nói không thành câu chỉ từng từ một thì đã nguy kịch phải gọi cấp cứu chưa?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P42-02', 'CHK-GINA_2023-P42-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P45-01', 'CHK-BYT_1851-P43-01', 'CHK-GINA_2023-P40-01']`
- **Chỉ số:** Recall = 0.0 | Precision = 0.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC02
- **Câu hỏi:** Bệnh nhân hen đang thở rít mà tự nhiên lơ mơ ngủ gà, lồng ngực im phăng phắc không nghe thấy tiếng thở nữa thì là bệnh đỡ hay nặng hơn?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P42-02', 'CHK-BYT_1851-P45-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P45-01', 'CHK-GINA_2023-P19-02', 'CHK-GINA_2023-P19-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC03
- **Câu hỏi:** Nửa đêm đột ngột lên cơn hen khó thở khò khè tại nhà thì các bước xịt thuốc xử trí cấp tốc ban đầu như thế nào?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P42-01', 'CHK-BYT_1851-P46-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P45-01', 'CHK-BYT_1851-P43-01', 'CHK-GINA_2023-P42-02']`
- **Chỉ số:** Recall = 0.0 | Precision = 0.0 | Faithfulness = 0.9 | Relevance = 0.95

### TC04
- **Câu hỏi:** Tôi tự thổi máy đo lưu lượng đỉnh PEF tại nhà thấy kim tụt xuống dưới 60% chỉ số tốt nhất của mình thì phải xử trí thế nào?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P41-01', 'CHK-GINA_2023-P42-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P41-01', 'CHK-GINA_2023-P35-02', 'CHK-BYT_1851-P28-02']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC05
- **Câu hỏi:** Bác sĩ hướng dẫn khi cơn hen trở nặng thì uống viên thuốc corticoid (prednisolone), vậy liều uống bao nhiêu và dùng trong mấy ngày?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P41-01', 'CHK-GINA_2023-P42-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P41-01', 'CHK-GINA_2023-P35-02', 'CHK-BYT_1851-P43-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC06
- **Câu hỏi:** Tôi dùng bình xịt thuốc hen duy trì mấy ngày nay thấy bị rát họng, khàn tiếng và có mảng trắng trong miệng thì xử trí thế nào?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P48-01', 'CHK-BYT_1851-P24-02']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P48-01', 'CHK-BYT_1851-P24-02', 'CHK-GINA_2023-P34-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC07
- **Câu hỏi:** Xịt thuốc cắt cơn Salbutamol xong tôi thấy tay bị run lẩy bẩy với tim đập nhanh hồi hộp thì có nguy hiểm không bác sĩ?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P48-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P44-01', 'CHK-GINA_2023-P48-02', 'CHK-GINA_2023-P48-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 0.5 | Faithfulness = 1.0 | Relevance = 0.95

### TC08
- **Câu hỏi:** Tại sao bác sĩ lại chỉ định cho tôi phải hít thuốc qua một ống nhựa buồng đệm (spacer) mà không hít trực tiếp bằng miệng?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P34-01', 'CHK-BYT_1851-P24-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P24-02', 'CHK-BYT_1851-P33-03', 'CHK-GINA_2023-P34-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 0.8333 | Faithfulness = 1.0 | Relevance = 0.95

### TC09
- **Câu hỏi:** Mấy tuần nay tôi thấy người hoàn toàn bình thường, hết ho khó thở rồi thì tôi có được tự dừng bình xịt duy trì hàng ngày không?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P33-03', 'CHK-BYT_1851-P21-03']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P27-01', 'CHK-BYT_1851-P21-03', 'CHK-BYT_1851-P09-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 0.5 | Faithfulness = 1.0 | Relevance = 0.95

### TC10
- **Câu hỏi:** Bị hen phế quản thì có đi tập gym hay chạy bộ được không, trước khi tập có cần chuẩn bị thuốc gì không?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P28-02', 'CHK-BYT_1851-P23-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P23-02', 'CHK-BYT_1851-P18-01', 'CHK-GINA_2023-P10-03']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC11
- **Câu hỏi:** Làm thế nào để tôi tự kiểm tra xem trong 4 tuần vừa qua bệnh hen của mình đang được kiểm soát tốt hay chưa kiểm soát?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P20-01', 'CHK-BYT_1851-P12-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P12-02', 'CHK-GINA_2023-P20-02', 'CHK-BYT_1851-P40-02']`
- **Chỉ số:** Recall = 0.0 | Precision = 0.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC12
- **Câu hỏi:** Tôi đang mang thai 3 tháng mà bị hen phế quản thì có được tiếp tục dùng bình xịt hen không, thuốc có ảnh hưởng thai nhi không?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P30-01', 'CHK-GINA_2023-P45-02']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P30-01', 'CHK-GINA_2023-P45-02', 'CHK-GINA_2023-P45-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC13
- **Câu hỏi:** Người bị bệnh hen phế quản khi bị đau nhức xương khớp hay cảm sốt thì có được tự mua thuốc giảm đau Paracetamol hay Ibuprofen/Aspirin uống không?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P46-01', 'CHK-BYT_1851-P31-01']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P29-01', 'CHK-GINA_2023-P29-02', 'CHK-BYT_1851-P23-01']`
- **Chỉ số:** Recall = 0.0 | Precision = 0.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC14
- **Câu hỏi:** Tôi bị hen mà hay bị ợ chua nóng rát ở ngực, liệu bệnh trào ngược dạ dày thực quản này có làm cơn hen khó thở nặng hơn không?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P46-02', 'CHK-BYT_1851-P32-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P32-01', 'CHK-GINA_2023-P46-02', 'CHK-GINA_2023-P46-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC15
- **Câu hỏi:** Người lớn mắc bệnh hen phế quản mạn tính có cần đi tiêm phòng cúm và phế cầu hàng năm không?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P23-01', 'CHK-GINA_2023-P29-01']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P29-01', 'CHK-BYT_1851-P23-01', 'CHK-GINA_2023-P29-02']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC16
- **Câu hỏi:** Sau khi vừa ra viện điều trị đợt cấp hen phế quản, tôi cần tái khám lại sau bao lâu và cần kiểm tra những gì?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P48-01', 'CHK-GINA_2023-P44-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P48-02', 'CHK-BYT_1851-P43-02', 'CHK-BYT_1851-P49-01']`
- **Chỉ số:** Recall = 0.0 | Precision = 0.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC17
- **Câu hỏi:** Mỗi lần đến lịch tái khám định kỳ hen phế quản thì tôi cần mang theo những gì và bác sĩ sẽ kiểm tra các nội dung gì?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P33-02', 'CHK-BYT_1851-P24-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P24-01', 'CHK-GINA_2023-P33-02', 'CHK-GINA_2023-P33-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC18
- **Câu hỏi:** Tôi bị hen mà kèm theo hắt hơi sổ mũi dị ứng quanh năm thì có cần điều trị viêm mũi dị ứng đồng thời không?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P31-02', 'CHK-GINA_2023-P46-02']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P46-02', 'CHK-GINA_2023-P46-01', 'CHK-BYT_1851-P23-01']`
- **Chỉ số:** Recall = 1.0 | Precision = 0.5 | Faithfulness = 1.0 | Relevance = 0.95

### TC19
- **Câu hỏi:** Bố tôi lớn tuổi có tiền sử hút thuốc lá nhiều năm, vừa được chẩn đoán hen lại vừa nghi mắc COPD thì điều trị có khác biệt gì?
- **Ground Truth Chunks:** `['CHK-GINA_2023-P47-01', 'CHK-BYT_1851-P33-01']`
- **Retrieved Chunks:** `['CHK-BYT_1851-P33-01', 'CHK-GINA_2023-P47-01', 'CHK-BYT_1851-P33-02']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95

### TC20
- **Câu hỏi:** Người nhà hút thuốc lá trong nhà có làm tăng nguy cơ bùng phát cơn hen cấp và làm giảm tác dụng của thuốc xịt không?
- **Ground Truth Chunks:** `['CHK-BYT_1851-P22-01', 'CHK-GINA_2023-P28-01']`
- **Retrieved Chunks:** `['CHK-GINA_2023-P28-01', 'CHK-BYT_1851-P22-01', 'CHK-GINA_2023-P27-02']`
- **Chỉ số:** Recall = 1.0 | Precision = 1.0 | Faithfulness = 1.0 | Relevance = 0.95
