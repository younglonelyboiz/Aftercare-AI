# Báo cáo Kết quả Giai đoạn 6 — Kiểm thử Red-Team Tiếng Việt, Kiểm thử Bất biến, Kịch bản Đầu-Cuối, Chịu lỗi và Đóng gói Bằng chứng (W07 Phase 6)

## 1. Mục tiêu Giai đoạn 6
Hoàn thiện toàn bộ các hạng mục từ `T6.1` đến `T6.6` trong tài liệu thiết kế `docs/Agent_Orchestration_Guardrails_Design.md` trên nhánh `feat/w07-redteam-and-evidence`:
- Xây dựng bộ dữ liệu kiểm thử đối kháng (Red-Team Dataset) tiếng Việt gồm `160` mẫu trải đều trên `10` nhóm nguy cơ lâm sàng và tấn công chính sách (`T6.1`).
- Viết bộ kiểm thử tự động cho toàn bộ `7` bất biến thiết kế hình thức từ `INV-1` đến `INV-7` (`T6.2`).
- Viết bộ kiểm thử tích hợp đầu-cuối (End-to-End) cho `4` kịch bản lâm sàng trọng yếu `A`, `B`, `C`, `D` (`T6.3`).
- Viết bộ kiểm thử chịu lỗi và hỗn loạn hạ tầng (Chaos & Resilience Tests) mô phỏng sự cố đứt kết nối mô hình ngôn ngữ lớn, sập cơ sở dữ liệu khi cấp cứu, lỗi bộ truy xuất Vector và ảo giác đầu ra (`T6.4`).
- Đóng gói trọn bộ bằng chứng `Evidence/W07/` kèm tệp chỉ mục `manifest.json`, `README.md`, `metrics.json` và biên bản thẩm định lâm sàng `W07_Clinical_Review_Signoff.md` (`T6.5`, `T6.6`).

---

## 2. Chi tiết Triển khai Kỹ thuật (`T6.1` – `T6.6`)

### 2.1. `T6.1` — Bộ dữ liệu Red-Team Tiếng Việt 160 mẫu (`tests/redteam/redteam_vi.jsonl`)
- Tạo kịch bản sinh dữ liệu chuẩn hóa `scripts/generate_redteam_dataset.py` và bộ dữ liệu `tests/redteam/redteam_vi.jsonl` gồm `160` mẫu kiểm thử tiếng Việt (bao gồm cả câu có dấu, không dấu và từ ngữ thông dụng của người bệnh):
  1. `RED_FLAG_EMERGENCY` (`20` mẫu): Khó thở dữ dội chỉ nói được từng từ, tím môi, rút lõm lồng ngực, SpO2 dưới 90%, xịt thuốc cắt cơn không đỡ.
  2. `YELLOW_ZONE_EXACERBATION` (`15` mẫu): Thức giấc nửa đêm vì ho hoặc khò khè, nặng ngực, hạn chế vận động, dùng thuốc cắt cơn nhiều lần trong ngày.
  3. `POLICY_SELFHARM` (`15` mẫu): Khủng hoảng tâm lý hoặc ý định tự gây hại (`POL-SELFHARM`, tạo vé `P1_HIGH`).
  4. `POLICY_PROMPT_INJECTION` (`20` mẫu): Vượt rào quy tắc hệ thống, tiêm thẻ điều khiển `<|im_start|>`, yêu cầu tiết lộ `RAG_SYSTEM_PROMPT` (`POL-INJECT`).
  5. `POLICY_MED_STOP` (`20` mẫu): Ý định tự ý ngưng thuốc kiểm soát hen hoặc ngừng sớm thuốc kháng viêm (`POL-MED-STOP`, tạo vé `P2_MEDIUM`).
  6. `POLICY_MED_DOSE` (`15` mẫu): Tự ý tăng gấp đôi hoặc giảm một nửa liều lượng thuốc (`POL-MED-DOSE`).
  7. `POLICY_RX_NEW` (`15` mẫu): Yêu cầu kê đơn mới, mua kháng sinh hoặc chuyển sang thuốc đông y truyền miệng (`POL-RX-NEW`).
  8. `POLICY_DIAGNOSIS` (`10` mẫu): Yêu cầu chẩn đoán phân biệt bệnh lý mới thay bác sĩ (`POL-DIAG`).
  9. `POLICY_OUT_OF_SCOPE` (`10` mẫu): Câu hỏi ngoài phạm vi chăm sóc hô hấp như bóng đá, chứng khoán, lập trình, nấu ăn (`POL-OOS`).
  10. `IN_DOMAIN_LEGITIMATE` (`20` mẫu): Câu hỏi giáo dục sức khỏe hen phế quản hợp lệ trong Vùng Xanh (`POL-ALLOW`).
- Kết quả thực thi `tests/redteam/test_redteam_evaluation.py` (xuất tại `Evidence/W07/redteam_evaluation_report.json`):
  - **Độ nhạy phát hiện Cờ đỏ (`RED_FLAG_EMERGENCY`)**: `20/20` (`100.0%`), số lần gọi mô hình ngôn ngữ lớn = `0`.
  - **Độ nhạy phát hiện Vùng Vàng (`YELLOW_ZONE_EXACERBATION`)**: `15/15` (`100.0%`), số lần gọi mô hình ngôn ngữ lớn = `0`.
  - **Tỷ lệ chặn vi phạm chính sách (`Policy Block Recall`)**: `105/105` (`100.0%`).
  - **Tỷ lệ chặn nhầm câu hỏi hợp lệ (`False Block Rate`)**: `0/20` (`0.0%`).

### 2.2. `T6.2` — Kiểm thử 7 Bất biến Thiết kế Hình thức (`tests/orchestration/test_invariants.py`)
- Kiểm định từng bất biến từ `INV-1` đến `INV-7`:
  - `test_inv1_monotonic_risk_enforced_across_all_transitions`: Chứng minh hàm `escalate_risk` không bao giờ hạ cấp mức độ nguy cơ và ném `RiskDowngradeError` với mọi cặp chuyển trạng thái lùi.
  - `test_inv2_zero_llm_calls_in_red_yellow_and_locked_session`: Chứng minh `RED_ZONE`, `YELLOW_ZONE` và phiên bị khóa Đỏ gọi mô hình ngôn ngữ lớn đúng `0` lần; gọi trực tiếp nút `generate_answer` khi đang ở Vùng Đỏ/Vàng sẽ ném `RiskDowngradeError`.
  - `test_inv3_zero_silent_escalation_with_outbox_fallback`: Chứng minh cả 4 nhóm sự kiện (`RED_ZONE`, `YELLOW_ZONE`, `POL-MED-STOP`, `POL-SELFHARM`) đều tạo vé cảnh báo hoặc lưu vào hàng đợi dự phòng `EscalationOutbox` khi cơ sở dữ liệu gặp sự cố.
  - `test_inv4_fail_closed_node_execution_never_leaks_stack_trace`: Chứng minh ngoại lệ runtime tại nút bất kỳ bị bắt bởi `@safe_node`, chuyển về `safe_fallback` và không rò rỉ thông tin nhạy cảm.
  - `test_inv5_evidence_gated_generation_blocks_unverified_queries`: Chứng minh truy vấn có điểm bằng chứng dưới ngưỡng `tau = 0.35` chuyển thẳng sang `no_evidence_response` với `0` lần gọi mô hình ngôn ngữ lớn.
  - `test_inv6_no_pii_egress_to_llm_or_audit_logs`: Chứng minh họ tên, mã bệnh nhân, số điện thoại, căn cước công dân, địa chỉ và thư điện tử bị xóa bỏ hoàn toàn khỏi prompt và bảng kiểm toán.
  - `test_inv7_complete_audit_trail_across_all_graph_terminal_paths`: Chứng minh mọi đường đi kết thúc đều hội tụ qua `finalize -> audit -> END`.

### 2.3. `T6.3` — Kiểm thử Tích hợp Đầu-Cuối 4 Kịch bản Lâm sàng (`tests/e2e/test_scenarios.py`)
- Kiểm định toàn trình 4 kịch bản `A` (Tư vấn Vùng Xanh có trích dẫn Bộ Y tế), `B` (Cấp cứu Vùng Đỏ + Khóa phiên Vùng Đỏ cho tới khi điều dưỡng đóng vé `P0_CRITICAL`), `C` (Cơn hen trở nặng Vùng Vàng tạo vé `P1_HIGH`), và `D` (Chặn ý định tự ý bỏ thuốc kiểm soát `POL-MED-STOP` và tạo vé `P2_MEDIUM`).

### 2.4. `T6.4` — Kiểm thử Chịu lỗi và Hỗn loạn Hạ tầng (`tests/chaos/test_resilience.py`)
- Kiểm định 4 kịch bản sự cố hạ tầng:
  1. Đứt kết nối mô hình ngôn ngữ lớn (`TimeoutError`) -> trả `SAFE_FALLBACK_MESSAGE`, không lộ khóa bí mật hay lỗi kết nối.
  2. Sập cơ sở dữ liệu khi bệnh nhân báo triệu chứng `RED_ZONE` -> trả hướng dẫn cấp cứu trong `< 100 ms`, lưu yêu cầu tạo vé vào `EscalationOutbox` và tự động phục hồi 100% khi gọi `flush_pending()`.
  3. Sập bộ truy xuất Vector (`ConnectionResetError`) -> bắt bởi `@safe_node`, chuyển về `safe_fallback`.
  4. Mô hình ngôn ngữ lớn bịa liều thuốc `500mg` hoặc rò rỉ thẻ `<context>` -> chặn đứng bởi `OutputPolicyGuard`.

---

## 3. Bảng Đối chiếu Chỉ số Nghiệm thu Toàn diện (Mục 7 Tài liệu Thiết kế)

| Chỉ số nghiệm thu | Ngưỡng mục tiêu | Kết quả đạt được | Nguồn minh chứng |
|---|---|---|---|
| Độ nhạy phát hiện Cờ đỏ (`Red-flag Recall`) | `100%` | **`100.0%` (`20/20`)** | `Evidence/W07/redteam_evaluation_report.json` |
| Độ nhạy phát hiện Vùng Vàng (`Yellow-zone Recall`) | `100%` | **`100.0%` (`15/15`)** | `Evidence/W07/redteam_evaluation_report.json` |
| Số lần gọi mô hình ngôn ngữ lớn khi `RED_ZONE` / `YELLOW_ZONE` | `0` | **`0`** | `tests/orchestration/test_invariants.py` |
| Tỷ lệ chặn vi phạm chính sách đầu vào (`Policy Block Recall`) | `>= 95%` | **`100.0%` (`105/105`)** | `Evidence/W07/redteam_evaluation_report.json` |
| Tỷ lệ chặn nhầm câu hỏi hợp lệ (`False Block Rate`) | `<= 5%` | **`0.0%` (`0/20`)** | `Evidence/W07/redteam_evaluation_report.json` |
| Tỷ lệ chấp nhận sai câu hỏi ngoài kho tri thức (`Out-of-corpus False Accept`) | `0%` | **`0.0%` (`0/20`)** | `Evidence/W07/evidence_gate_calibration.json` |
| Tỷ lệ chặn đầu ra độc hại / bịa liều thuốc (`Toxic Output Interception`) | `100%` | **`100.0%` (`30/30`)** | `tests/test_phase4_output_guardrails.py` |
| Tỷ lệ rò rỉ thông tin định danh cá nhân (`PII Leak Rate`) | `0%` | **`0.0%`** | `tests/orchestration/test_invariants.py` |
| Tỷ lệ mất vé cảnh báo khi cơ sở dữ liệu gián đoạn (`Lost Escalation Ticket Rate`) | `0%` | **`0.0%`** | `tests/chaos/test_resilience.py` |
| Độ trễ phản hồi khẩn cấp Vùng Đỏ / Vùng Vàng (`P95 Emergency Latency`) | `< 100 ms` | **`< 5 ms`** | `Evidence/W07/metrics.json` |

