# Hồ sơ Bằng chứng Kỹ thuật và Kiểm định An toàn Tuần 7 (`Evidence/W07`)

Thư mục này lưu trữ toàn bộ báo cáo kết quả triển khai, dữ liệu hiệu chuẩn, kết quả kiểm thử đối kháng Red-Team, số liệu độ trễ thực nghiệm và biên bản thẩm định lâm sàng cho kiến trúc **Điều phối Đồ thị Tất định có Rào chắn An toàn Đa tầng (`W07-AGENT-ORCHESTRATION-GUARDRAILS`)** của hệ thống **Aftercare-AI**.

---

## 1. Danh mục Báo cáo theo Giai đoạn (`Phase 0` – `Phase 6`)

| Giai đoạn | Tệp báo cáo | Nội dung trọng tâm | Bộ kiểm thử tương ứng |
|---|---|---|---|
| **Giai đoạn 0** | `W07_Phase0_Safety_Fixes.md` | Khắc phục khẩn cấp 4 lỗ hổng an toàn (`T0.1` – `T0.4`): tự động tạo vé cảnh báo khi phát hiện cờ đỏ/cờ vàng qua Chatbot, cơ chế dự phòng lỗi mô hình ngôn ngữ lớn, thực thi bất đồng bộ và danh sách trắng mô hình. | `tests/test_phase0_safety.py` (`12/12` đạt) |
| **Giai đoạn 1** | `W07_Phase1_Orchestration_Foundation.md` | Xây dựng đồ thị điều phối tất định bằng `LangGraph StateGraph`, trạng thái `AftercareState`, hàm chuyển mức nguy cơ đơn điệu `escalate_risk`, decorator `@safe_node` và sơ đồ `figures/orchestration_graph.mmd`. | `tests/test_phase1_orchestration.py` (`28/28` đạt) |
| **Giai đoạn 2** | `W07_Phase2_Input_Guardrails.md` | Xây dựng hàng rào an toàn đầu vào (`L0` khử nhiễu, `L1` sàng lọc triệu chứng chạy trước cắt chuỗi, `L2` bộ quy tắc chính sách `input_policies.yaml`) và leo thang cảnh báo `POL-MED-STOP`, `POL-SELFHARM`. | `tests/test_phase2_input_guardrails.py` (`12/12` đạt) |
| **Giai đoạn 3** | `W07_Phase3_Evidence_And_Generation.md` | Xây dựng cổng kiểm chứng bằng chứng `EvidenceGate` (`tau = 0.35`), bộ ẩn danh thông tin cá nhân `PIIRedactor`, ranh giới XML chống tiêm lệnh gián tiếp và cơ chế khóa phiên Vùng Đỏ (`session_locked_red`). | `tests/test_phase3_evidence_and_generation.py` (`10/10` đạt) |
| **Giai đoạn 4** | `W07_Phase4_Output_Guardrails.md` | Xây dựng hàng rào an toàn đầu ra `OutputPolicyGuard` (`output_policies.yaml` gồm 9 quy tắc và 76 hoạt chất kiểm soát), chặn 100% đầu ra độc hại/bịa liều lượng và tự động chuẩn hóa trích dẫn Bộ Y tế. | `tests/test_phase4_output_guardrails.py` (`5/5` đạt) |
| **Giai đoạn 5** | `W07_Phase5_Audit_And_Escalation.md` | Xây dựng hàng đợi leo thang dự phòng `EscalationOutboxDispatcher`, bảng kiểm toán bất biến `agent_actions_log` / `audit_logs`, giao diện nhãn `Nguồn: Chatbot` và bộ thu thập độ trễ `P50`/`P95`. | `tests/test_phase5_audit_and_escalation.py` (`5/5` đạt) |
| **Giai đoạn 6** | `W07_Phase6_RedTeam_And_Evidence.md` | Kiểm thử bộ dữ liệu Red-Team tiếng Việt `160` mẫu, kiểm thử `7` bất biến thiết kế (`INV-1` – `INV-7`), `4` kịch bản đầu-cuối (`A`, `B`, `C`, `D`), `4` kịch bản chịu lỗi hỗn loạn (`Chaos`) và đóng gói bằng chứng. | `tests/redteam/`, `tests/orchestration/`, `tests/e2e/`, `tests/chaos/` (`16/16` đạt) |

---

## 2. Danh mục Tệp Dữ liệu Thực nghiệm và Thẩm định

- `W07_Clinical_Review_Signoff.md`: Biên bản thẩm định lâm sàng và ký duyệt phiên bản `v1.0.0` cho `templates_vi.py`, `input_policies.yaml` và `output_policies.yaml`.
- `evidence_gate_calibration.json`: Báo cáo hiệu chuẩn thực nghiệm ngưỡng `tau = 0.35` của `EvidenceGate` (tỷ lệ chấp nhận sai câu hỏi ngoài kho tri thức = `0.0%`).
- `redteam_evaluation_report.json`: Báo cáo đánh giá thực nghiệm trên `160` mẫu Red-Team tiếng Việt (`Red-flag Recall = 100%`, `Yellow-zone Recall = 100%`, `Policy Block Recall = 100%`, `False Block Rate = 0%`).
- `metrics.json`: Báo cáo phân vị độ trễ `P50` và `P95` theo từng nút trên đồ thị điều phối.
- `figures/orchestration_graph.mmd`: Sơ đồ cấu trúc đồ thị `LangGraph StateGraph` được trích xuất tự động từ mã nguồn.
- `manifest.json`: Danh mục toàn bộ tệp bằng chứng trong `Evidence/W07/` kèm mã băm toàn vẹn `SHA-256`.

---

## 3. Lệnh Tái lập Kiểm chứng (Reproducibility Commands)

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_phase0_safety.py tests/test_phase1_orchestration.py tests/test_phase2_input_guardrails.py tests/test_phase3_evidence_and_generation.py tests/test_phase4_output_guardrails.py tests/test_phase5_audit_and_escalation.py tests/redteam/test_redteam_evaluation.py tests/orchestration/test_invariants.py tests/e2e/test_scenarios.py tests/chaos/test_resilience.py -v
```

