# W07 - Giai đoạn 2: Hàng rào An toàn Đầu vào (Input Guardrails)

**Nhánh:** `feat/w07-input-guardrails`
**Tài liệu thiết kế gốc:** [Agent_Orchestration_Guardrails_Design.md](../../docs/Agent_Orchestration_Guardrails_Design.md) — Mục 4.1, Mục 4.3 và Mục 6 (T2.1 đến T2.5)
**Kết quả kiểm thử:** `tests/test_phase2_input_guardrails.py` (12 bài kiểm thử, bao gồm 22 mẫu tấn công/vi phạm và 22 câu hỏi lâm sàng hợp lệ từ Golden Dataset), toàn bộ bộ kiểm thử Giai đoạn 0, Giai đoạn 1 và RBAC/Chat Memory đều đạt 100%.

---

## 1. NỘI DUNG GỢI Ý CHO GITHUB ISSUE

```markdown
**Title:** [W07][Guardrails]Xây dựng hàng rào an toàn đầu vào và bộ quy tắc chính sách YAML (T2.1 - T2.5)

### Bối cảnh
Triển khai Giai đoạn 2 trong thiết kế Agent Orchestration & Guardrails (`docs/Agent_Orchestration_Guardrails_Design.md`): xây dựng bộ làm sạch đầu vào L0 (`sanitize_input`) và bộ kiểm soát chính sách đầu vào L2 (`InputPolicyGuard`) dựa trên cấu hình YAML có phiên bản, đảm bảo nguyên tắc "Safety trước Policy" và kết nối leo thang cảnh báo khi người bệnh có ý định tự ý bỏ thuốc hoặc tự gây hại.

### Danh sách nhiệm vụ
- [x] **T2.1:** Hoàn thiện nút `sanitize_input` (L0): lọc ký tự điều khiển, ký tự zero-width, chuẩn hóa ký tự đồng hình (homoglyph), xử lý chuỗi rỗng (`IN-EMPTY`) và giới hạn 2.000 ký tự (`IN-LEN`) mà vẫn bảo toàn văn bản đầy đủ cho `safety_triage`.
- [x] **T2.2:** Soạn tệp cấu hình `backend/app/guardrails/policies/input_policies.yaml` cho 7 quy tắc chính sách (`POL-SELFHARM`, `POL-INJECT`, `POL-MED-STOP`, `POL-MED-DOSE`, `POL-RX-NEW`, `POL-DIAG`, `POL-OOS`) hỗ trợ cả tiếng Việt có dấu, không dấu và từ viết tắt.
- [x] **T2.3:** Xây dựng `InputPolicyGuard` (`backend/app/guardrails/input_guard.py`) và kết nối vào nút `policy_guard` cùng `safe_refusal`; đạt độ nhạy chặn (Recall) 100% (>= 95%) và tỷ lệ chặn nhầm (False-block) 0% (<= 5%) trên tập câu hỏi hợp lệ của Golden Dataset.
- [x] **T2.4:** Kiểm thử khẳng định thứ tự ưu tiên tuyệt đối "Safety trước Policy": mọi tin nhắn vừa chứa Prompt Injection hoặc yêu cầu đổi thuốc vừa chứa dấu hiệu Cờ Đỏ đều được phân loại vào `RED_ZONE` và sinh vé `P0_CRITICAL`.
- [x] **T2.5:** Kết nối các quy tắc `POL-MED-STOP` (sinh vé `P2_MEDIUM` loại `MEDICATION_NONADHERENCE_INTENT`) và `POL-SELFHARM` (sinh vé `P1_HIGH` loại `MENTAL_HEALTH_CONCERN`) sang `EscalationService`.

### Tiêu chí hoàn thành
- Không có bất kỳ lời gọi LLM nào khi tin nhắn bị chặn bởi L0 (`IN-EMPTY`) hoặc L2 (`POL-*`).
- Cờ Đỏ nằm ở phần cuối của tin nhắn dài trên 2.000 ký tự hoặc đi kèm câu lệnh Prompt Injection vẫn luôn kích hoạt `RED_ZONE` và tạo vé `P0_CRITICAL`.
- Đạt 100% bài kiểm thử Giai đoạn 2 (`tests/test_phase2_input_guardrails.py`) và toàn bộ bài kiểm thử hồi quy của hệ thống.
```

---

## 2. TÓM TẮT CÁC NHIỆM VỤ ĐÃ HOÀN THÀNH

| Mã nhiệm vụ | Nội dung thực hiện | Trạng thái | Tệp mã nguồn chính |
| :--- | :--- | :---: | :--- |
| **T2.1** | Chuẩn hóa Unicode NFKC/NFC, khử ký tự zero-width, ký tự điều khiển và ký tự đồng hình (homoglyph); xử lý `IN-EMPTY` và `IN-LEN` (> 2.000 ký tự) | Đã hoàn thành | `backend/app/orchestration/nodes/sanitize.py` |
| **T2.2** | Định nghĩa 7 quy tắc chính sách đầu vào trong YAML (mẫu có dấu, không dấu, mẫu ngoại lệ hợp lệ, cấu hình leo thang và mẫu phản hồi tiếng Việt) | Đã hoàn thành | `backend/app/guardrails/policies/input_policies.yaml` |
| **T2.3** | Xây dựng `InputPolicyGuard` nạp quy tắc YAML, tái sử dụng bộ chuẩn hóa của `SymptomScreenerEngine`, gắn vào nút `policy_guard` | Đã hoàn thành | `backend/app/guardrails/input_guard.py`, `backend/app/orchestration/nodes/policy_guard.py` |
| **T2.4** | Kiểm chứng thứ tự ưu tiên "Safety Triage trước Policy Guard" trên các mẫu trộn lẫn tấn công và dấu hiệu suy hô hấp cấp | Đã hoàn thành | `tests/test_phase2_input_guardrails.py` |
| **T2.5** | Tự động tạo `AlertTicket` mức `P2_MEDIUM` cho `POL-MED-STOP` và mức `P1_HIGH` cho `POL-SELFHARM` qua `EscalationService` | Đã hoàn thành | `backend/app/api/v1/endpoints/chat.py`, `backend/app/rag/service.py`, `backend/app/orchestration/state.py` |

---

## 3. CHI TIẾT KỸ THUẬT

### 3.1. Làm sạch đầu vào và bảo toàn Cờ Đỏ trên văn bản dài (T2.1)
- Hàm `sanitize_text_preserve_length()` chuẩn hóa tương thích `NFKC`, ánh xạ các ký tự đồng hình hệ Cyrillic/Hy Lạp về chữ cái Latin chuẩn, chuẩn hóa `NFC` và loại bỏ toàn bộ ký tự điều khiển cùng ký tự ẩn zero-width (`\u200b-\u200f`, `\u202a-\u202e`, `\u2060-\u206f`, `\ufeff`).
- Khi tin nhắn vượt quá 2.000 ký tự (`IN-LEN`): `clean_message` được cắt về 2.000 ký tự để phục vụ truy xuất RAG, nhưng `raw_message` giữ nguyên toàn bộ văn bản đã làm sạch ký tự ẩn để nút `safety_triage` quét trọn vẹn triệu chứng (tránh bỏ sót dấu hiệu Cờ Đỏ ở cuối đoạn văn dài).

### 3.2. Bảy quy tắc chính sách đầu vào trong YAML (T2.2 và T2.3)
Tệp `backend/app/guardrails/policies/input_policies.yaml` định nghĩa 7 quy tắc theo thứ tự ưu tiên:
1. `POL-SELFHARM`: Phát hiện ý định tự gây hại hoặc khủng hoảng tâm lý -> chặn LLM, trả thông điệp hỗ trợ khẩn cấp và tạo vé `P1_HIGH` (`MENTAL_HEALTH_CONCERN`).
2. `POL-INJECT`: Phát hiện câu lệnh Prompt Injection / Jailbreak (tiếng Việt và tiếng Anh) yêu cầu bỏ qua hướng dẫn hệ thống, đóng vai bác sĩ kê đơn hoặc trích xuất system prompt -> chặn LLM.
3. `POL-MED-STOP`: Phát hiện ý định tự ý ngưng hoặc bỏ thuốc kiểm soát hen (Symbicort, Seretide, ICS) hoặc dừng sớm thuốc viên kháng viêm (Prednisolone, Methylprednisolone) -> chặn LLM, trả lời giải thích cơ chế viêm đường thở kèm trích dẫn Hướng dẫn Bộ Y tế Mục 2.7.2 và tạo vé `P2_MEDIUM` (`MEDICATION_NONADHERENCE_INTENT`). Có danh sách mẫu cho phép (`allow_patterns`) để không chặn nhầm câu hỏi tìm hiểu kiến thức hợp lệ.
4. `POL-MED-DOSE`: Phát hiện ý định tự ý tăng gấp đôi hoặc giảm liều thuốc ngoài đơn -> chặn LLM, nhắc giữ đúng liều trong Kế hoạch hành động hen.
5. `POL-RX-NEW`: Phát hiện yêu cầu kê đơn thuốc mới, hỏi mua kháng sinh hoặc thay thuốc xịt bằng thuốc nam/thuốc bắc -> chặn LLM.
6. `POL-DIAG`: Phát hiện yêu cầu chẩn đoán xác định bệnh lý mới (viêm phổi, lao phổi, ung thư phổi, suy tim) -> chặn LLM.
7. `POL-OOS`: Phát hiện câu hỏi ngoài phạm vi chăm sóc hô hấp (chứng khoán, tiền ảo, lập trình, bóng đá, toán học) -> chặn LLM.

### 3.3. Kết quả đo lường chất lượng bộ lọc (T2.3, T2.4, T2.5)
- **Độ nhạy chặn vi phạm (Policy Recall):** Đạt **22/22 (100%)** trên tập mẫu tấn công và vi phạm chính sách (mục tiêu thiết kế: >= 95%).
- **Tỷ lệ chặn nhầm câu hỏi hợp lệ (False-block Rate):** Đạt **0/22 (0,0%)** trên tập câu hỏi hợp lệ từ `Data/golden_dataset.json` và các câu hỏi chăm sóc sau xuất viện (mục tiêu thiết kế: <= 5%).
- **Thứ tự ưu tiên Safety trước Policy:** Đạt **100%** (4/4 kịch bản trộn lẫn Prompt Injection / đổi thuốc / ngoài phạm vi với triệu chứng Cờ Đỏ đều trả về `RED_ZONE` và tạo vé `P0_CRITICAL`).

---

## 4. DANH SÁCH TỆP THAY ĐỔI VÀ TẠO MỚI

```text
M  backend/app/api/v1/endpoints/chat.py
M  backend/app/guardrails/__init__.py
M  backend/app/orchestration/nodes/policy_guard.py
M  backend/app/orchestration/nodes/sanitize.py
M  backend/app/orchestration/state.py
M  backend/app/rag/service.py
M  docs/Agent_Orchestration_Guardrails_Design.md
A  backend/app/guardrails/input_guard.py
A  backend/app/guardrails/policies/input_policies.yaml
A  Evidence/W07/W07_Phase2_Input_Guardrails.md
A  tests/test_phase2_input_guardrails.py
```

**Câu lệnh commit gợi ý:**

```text
feat(guardrails): W07 phase 2 - L0 input sanitizer, L2 YAML policy guard and policy escalation (closes #<số_issue>)
```

