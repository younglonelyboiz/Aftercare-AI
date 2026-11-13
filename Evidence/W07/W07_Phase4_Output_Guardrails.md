# BÁO CÁO KẾT QUẢ GIAI ĐOẠN 4: HÀNG RÀO AN TOÀN ĐẦU RA VÀ KIỂM CHỨNG TRÍCH DẪN (W07 — PHASE 4)

**Ngày hoàn thành:** 13/11/2026  
**Nhánh làm việc:** `feat/w07-output-guardrails`  
**Tài liệu thiết kế tham chiếu:** [Agent_Orchestration_Guardrails_Design.md](../../docs/Agent_Orchestration_Guardrails_Design.md) — Mục 4.6 (L5 Output Guard) và Mục 6 (Giai đoạn 4)

---

## 1. Tóm tắt các hạng mục đã hoàn thành

| Mã nhiệm vụ | Nội dung công việc | Tệp mã nguồn chính | Trạng thái |
| :--- | :--- | :--- | :---: |
| **T4.1** | Xây dựng tệp cấu hình chính sách đầu ra `output_policies.yaml` định nghĩa đầy đủ 9 quy tắc theo Mục 4.6, danh mục 76 hoạt chất/biệt dược cần kiểm soát và các mẫu kiểm thử dương/âm cho từng quy tắc | `backend/app/guardrails/policies/output_policies.yaml` | Đã hoàn thành |
| **T4.2** | Xây dựng bộ máy kiểm duyệt đầu ra tất định `OutputPolicyGuard` thực thi kiểm tra rò rỉ thẻ nội bộ (`OUT-LEAK`), tái sàng lọc rủi ro (`OUT-RESCREEN`), trấn an tuyệt đối (`OUT-FALSE-REASSURE`), khuyên tự ngưng thuốc (`OUT-STOP-MED`), tự chẩn đoán (`OUT-DIAG`), bịa đặt liều lượng (`OUT-DOSE-LEAK`) và nhắc thuốc ngoài danh mục cho phép (`OUT-MED-ALLOW`) | `backend/app/guardrails/output_guard.py`, `backend/app/orchestration/nodes/output_guard.py` | Đã hoàn thành |
| **T4.3** | Xây dựng bộ xác thực và tự động chuẩn hóa trích dẫn nguồn tài liệu (`OUT-CITE`) cùng dòng lưu ý miễn trừ trách nhiệm y tế (`OUT-DISCLAIMER`) với quyết định `REWRITTEN` | `backend/app/guardrails/output_guard.py`, `backend/app/orchestration/nodes/output_guard.py` | Đã hoàn thành |

---

## 2. Chi tiết kỹ thuật

### 2.1. T4.1 — Cấu hình chính sách đầu ra (`output_policies.yaml`)
Tệp [output_policies.yaml](../../backend/app/guardrails/policies/output_policies.yaml) định nghĩa 9 quy tắc đầu ra theo thứ tự ưu tiên:
1. **`OUT-LEAK` (`action: FAIL`)**: Chặn phản hồi làm lộ các thẻ ranh giới XML nội bộ (`<context>`, `<care_context>`, `<patient_message>`), tên biến cấu hình (`RAG_SYSTEM_PROMPT`, `AftercareState`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) hoặc nhãn ẩn danh nội bộ (`[MÃ_BỆNH_NHÂN]`).
2. **`OUT-RESCREEN` (`action: RISK_UP`)**: Phát hiện trường hợp nội dung phản hồi khẳng định tình trạng hiện tại của người bệnh đang nguy kịch hoặc lên cơn hen cấp; tự động nâng mức rủi ro lên `YELLOW_ZONE` thông qua hàm `escalate_risk()` (tuân thủ bất biến `INV-1`) và định tuyến sang nút `action_plan_response`.
3. **`OUT-FALSE-REASSURE` (`action: FAIL`)**: Chặn các câu trấn an tuyệt đối gây chủ quan y khoa (ví dụ: *"chắc chắn không sao đâu"*, *"tuyệt đối không cần đi khám đâu"*, *"bệnh hen của bác đã khỏi hẳn hoàn toàn"*).
4. **`OUT-STOP-MED` (`action: FAIL`)**: Chặn câu trả lời khuyên người bệnh tự ý ngưng, bỏ hoặc dừng hẳn thuốc dự phòng, đồng thời phân biệt chính xác với câu cảnh báo hợp lệ có tiền tố phủ định (*"tuyệt đối không được tự ý ngưng thuốc"*).
5. **`OUT-DIAG` (`action: FAIL`)**: Chặn câu trả lời tự đưa ra kết luận chẩn đoán xác định thay bác sĩ (ví dụ: *"Tôi chẩn đoán rằng bác đã bị bệnh viêm phổi"*).
6. **`OUT-DOSE-LEAK` (`action: FAIL`)**: Trích xuất toàn bộ biểu thức con số kèm đơn vị liều lượng (`mg`, `mcg`, `nhát`, `viên`, `ống`, `ml`) trong câu trả lời và đối chiếu với ngữ cảnh hợp lệ của lượt hội thoại (`retrieved_chunks` hợp với `profile`, `clean_message` và `history`, có hỗ trợ khoảng liều như `2-4 nhát`). Nếu xuất hiện bất kỳ con số liều lượng nào không có trong nguồn đối chiếu, phản hồi bị chặn và chuyển sang thông điệp dự phòng an toàn (`SAFE_FALLBACK_MESSAGE`).
7. **`OUT-MED-ALLOW` (`action: FAIL`)**: Quét 76 tên hoạt chất và biệt dược trong `controlled_medications_catalog` (kháng sinh, thuốc an thần, thuốc giảm đau kháng viêm không steroid, corticoid đường toàn thân, thuốc giãn phế quản...). Chỉ cho phép các thuốc đã xuất hiện trong đoạn tài liệu truy xuất, kế hoạch điều trị của bệnh nhân hoặc câu hỏi hiện tại (kèm ánh xạ cặp biệt dược và hoạt chất tương đương như `Symbicort` với `Budesonide`/`Formoterol`, `Ventolin` với `Salbutamol`).
8. **`OUT-CITE` (`action: REWRITE`)**: Kiểm tra dòng `Tài liệu tham khảo:` ở cuối câu trả lời. Nếu thiếu trích dẫn hoặc trích dẫn bịa đặt không khớp với bất kỳ từ khóa nguồn nào của `retrieved_chunks`, hệ thống tự động gắn hoặc thay thế bằng trích dẫn chuẩn từ `retrieved_chunks` và ghi nhận `GuardEvent(rule_id="OUT-CITE", decision="REWRITTEN")`.
9. **`OUT-DISCLAIMER` (`action: REWRITE`)**: Kiểm tra sự hiện diện của dòng lưu ý miễn trừ trách nhiệm y tế; nếu thiếu sẽ tự động gắn vào cuối văn bản và ghi nhận `GuardEvent(rule_id="OUT-DISCLAIMER", decision="REWRITTEN")`.

---

## 3. Kết quả kiểm thử nghiệm thu

Chạy bộ kiểm thử Giai đoạn 4 tại [test_phase4_output_guardrails.py](../../tests/test_phase4_output_guardrails.py):

```text
tests/test_phase4_output_guardrails.py::test_t41_output_policies_yaml_has_9_rules_and_samples PASSED
tests/test_phase4_output_guardrails.py::test_t42_30_toxic_outputs_100_percent_intercepted PASSED
tests/test_phase4_output_guardrails.py::test_t42_20_standard_outputs_pass_rate PASSED
tests/test_phase4_output_guardrails.py::test_t43_missing_or_fabricated_citation_and_disclaimer_are_rewritten PASSED
tests/test_phase4_output_guardrails.py::test_t43_graph_end_to_end_output_guard_blocks_and_rewrites PASSED
```

| Chỉ số đánh giá | Kết quả đạt được | Mục tiêu thiết kế (Mục 6 & Mục 7) |
| :--- | :---: | :---: |
| Số quy tắc chính sách đầu ra trong `output_policies.yaml` | **9 / 9 quy tắc** | 9 quy tắc |
| Tỷ lệ chặn trên 30 câu trả lời độc hại tổng hợp (`TOXIC_SYNTHETIC_OUTPUTS`) | **30 / 30 (100.0%)** | 100% (0 / 30 câu lọt) |
| Tỷ lệ vượt qua trên 20 câu trả lời chuẩn mực (`STANDARD_VALID_OUTPUTS`) | **20 / 20 (100.0%)** | >= 95% |
| Tỷ lệ phản hồi nhánh `NORMAL` có trích dẫn khớp đoạn tài liệu truy xuất | **100.0%** | 100% |
| Tổng số bài kiểm thử tự động các giai đoạn 0, 1, 2, 3, 4 và phân quyền bộ nhớ | **60 / 60 đạt (100%)** | 100% đạt |

