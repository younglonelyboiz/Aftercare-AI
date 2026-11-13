# BÁO CÁO KẾT QUẢ GIAI ĐOẠN 5: HÀNG ĐỢI LEO THANG OUTBOX, NHẬT KÝ KIỂM TOÁN BẤT BIẾN VÀ ĐO LƯỜNG QUAN SÁT (W07 — PHASE 5)

**Ngày hoàn thành:** 13/11/2026  
**Nhánh làm việc:** `feat/w07-escalation-and-audit`  
**Tài liệu thiết kế tham chiếu:** [Agent_Orchestration_Guardrails_Design.md](../../docs/Agent_Orchestration_Guardrails_Design.md) — Mục 4.7 (L6 Escalation Dispatcher), Mục 4.8 (L7 Audit & Observability) và Mục 6 (Giai đoạn 5)

---

## 1. Tóm tắt các hạng mục đã hoàn thành

| Mã nhiệm vụ | Nội dung công việc | Tệp mã nguồn chính | Trạng thái |
| :--- | :--- | :--- | :---: |
| **T5.1** | Bổ sung các mã loại cảnh báo sinh từ Chatbot vào `AlertTicketDTO` (`source_channel`, `alert_type_label`) và hiển thị nhãn `"Nguồn: Chatbot"` trên giao diện điều dưỡng | `backend/app/schemas/care_tracker.py`, `frontend/src/components/Nurse/NurseCommandCenter.jsx`, `frontend/src/components/Nurse/LiveAlertBanner.jsx` | Đã hoàn thành |
| **T5.2** | Xây dựng mô hình hàng đợi dự phòng `EscalationOutbox` (`escalation_outbox`) và bộ điều phối `EscalationOutboxDispatcher` đảm bảo không mất vé cảnh báo khi cơ sở dữ liệu hoặc dịch vụ cảnh báo tạm thời gián đoạn | `backend/app/models/audit.py`, `backend/app/orchestration/nodes/escalate.py`, `backend/app/api/v1/endpoints/chat.py` | Đã hoàn thành |
| **T5.3** | Xây dựng kịch bản khởi tạo hai bảng kiểm toán chỉ thêm mới (`agent_actions_log`, `audit_logs`), lưu mã băm SHA-256 kèm văn bản đã ẩn danh thông tin cá nhân và cưỡng chế không cho phép sửa/xóa bản ghi (`ImmutableAuditRecordError`) | `backend/app/models/audit.py`, `backend/app/db/migrate_audit_tables.py`, `backend/app/orchestration/nodes/finalize_audit.py` | Đã hoàn thành |
| **T5.4** | Xây dựng endpoint chỉ đọc dành riêng cho quản trị viên `GET /api/v1/audit/traces/{trace_id}` và `GET /api/v1/audit/metrics` | `backend/app/api/v1/endpoints/audit.py`, `backend/app/api/v1/router.py` | Đã hoàn thành |
| **T5.5** | Xây dựng bộ thu thập chỉ số quan sát `OrchestrationMetricsCollector` tính phân vị độ trễ `P50`/`P95` theo từng nút của đồ thị và xuất tệp `Evidence/W07/metrics.json` | `backend/app/orchestration/nodes/finalize_audit.py`, `Evidence/W07/metrics.json` | Đã hoàn thành |

---

## 2. Chi tiết kỹ thuật

### 2.1. T5.1 — Phân biệt nguồn cảnh báo Chatbot trên Schema và Giao diện Điều dưỡng
- Trong [care_tracker.py](../../backend/app/schemas/care_tracker.py):
  - Bổ sung tập hợp `CHAT_ALERT_TYPES` gồm 5 mã loại cảnh báo từ luồng hội thoại (`CHAT_RED_FLAG_DETECTION`, `CHAT_YELLOW_ZONE_ALERT`, `MEDICATION_NONADHERENCE_INTENT`, `MENTAL_HEALTH_CONCERN`, `SYSTEM_DEGRADED_PATIENT_UNSERVED`) cùng bảng ánh xạ nhãn tiếng Việt `ALERT_TYPE_LABELS_VI`.
  - Bổ sung validator tự động điền `source_channel = "CHATBOT"` (hoặc `"CHECKIN"`) và `alert_type_label` trên `AlertTicketDTO`.
- Trong [LiveAlertBanner.jsx](../../frontend/src/components/Nurse/LiveAlertBanner.jsx) và [NurseCommandCenter.jsx](../../frontend/src/components/Nurse/NurseCommandCenter.jsx):
  - Hiển thị huy hiệu **"Nguồn: Chatbot"** kèm mức độ ưu tiên và lý do kích hoạt ngay trên thanh báo động khẩn cấp và thẻ bệnh nhân của điều dưỡng.

### 2.2. T5.2 — Hàng đợi leo thang dự phòng (`EscalationOutboxDispatcher`)
- Triển khai tại [escalate.py](../../backend/app/orchestration/nodes/escalate.py) và kết nối vào `escalate_chat_result` trong [chat.py](../../backend/app/api/v1/endpoints/chat.py):
  - Khi `escalation_service.create_or_escalate_ticket()` thành công, trả về mã vé ngay lập tức.
  - Khi cơ sở dữ liệu hoặc dịch vụ cảnh báo gặp sự cố tạm thời, hệ thống không làm gián đoạn câu trả lời cấp cứu gửi tới bệnh nhân (tuân thủ nguyên tắc không chặn luồng chính) mà tự động ghi bản ghi `PENDING` vào bảng `escalation_outbox` (kèm cơ chế ghi tệp dự phòng `.jsonl` trên đĩa nếu kết nối cơ sở dữ liệu bị ngắt hoàn toàn).
  - Phương thức `flush_pending()` đồng bộ lại toàn bộ bản ghi từ tệp dự phòng và bảng `escalation_outbox`, thực thi tạo lại `AlertTicket` và cập nhật trạng thái `status = "SENT"`, đảm bảo tỷ lệ mất vé bằng `0`.

### 2.3. T5.3 — Nhật ký hành động và Kiểm toán bất biến (`agent_actions_log` & `audit_logs`)
- Triển khai tại [audit.py](../../backend/app/models/audit.py), [migrate_audit_tables.py](../../backend/app/db/migrate_audit_tables.py) và [finalize_audit.py](../../backend/app/orchestration/nodes/finalize_audit.py):
  - Mỗi lượt hội thoại đi qua nút `audit` sẽ sinh **1 bản ghi `AgentActionLog`** và **N bản ghi `AuditLog`** (tương ứng với từng sự kiện `GuardEvent` theo thứ tự `sequence`), liên kết qua cùng một mã `trace_id`.
  - Tin nhắn gốc không bao giờ được lưu thô vào bảng kiểm toán: hệ thống chỉ lưu mã băm `message_sha256` (`SHA-256`) và chuỗi `redacted_message` đã đi qua `PIIRedactor`.
  - Cưỡng chế tính chất chỉ thêm mới (`append-only`) ở tầng ORM bằng sự kiện `before_update` và `before_delete`: mọi nỗ lực sửa hoặc xóa bản ghi trong `agent_actions_log` hoặc `audit_logs` đều ném ngoại lệ `ImmutableAuditRecordError`.

### 2.4. T5.4 & T5.5 — Endpoint truy vết cho Quản trị viên và Thống kê độ trễ `P50`/`P95`
- Triển khai [audit.py](../../backend/app/api/v1/endpoints/audit.py) gắn tại tiền tố `/api/v1/audit` với quyền `Depends(admin_user)`:
  - `GET /api/v1/audit/traces/{trace_id}`: trả về thông tin tổng hợp của lượt hội thoại (`action`) và danh sách toàn bộ các bước đi qua hàng rào an toàn (`events`).
  - `GET /api/v1/audit/metrics`: trả về bản chụp thống kê độ trễ `P50`/`P95` theo từng nút (`node_latency_ms`), độ trễ đầu-cuối theo mức rủi ro (`end_to_end_latency_by_risk_ms`) và bộ đếm số lần chặn theo từng quy tắc (`guard_block_total`).
  - Tự động xuất tệp chỉ số thực nghiệm tại [metrics.json](metrics.json).

---

## 3. Kết quả kiểm thử tự động

Chạy bộ kiểm thử Giai đoạn 5 tại [test_phase5_audit_and_escalation.py](../../tests/test_phase5_audit_and_escalation.py):

```text
tests/test_phase5_audit_and_escalation.py::test_t51_alert_ticket_dto_populates_chatbot_channel_and_ui_badge PASSED
tests/test_phase5_audit_and_escalation.py::test_t52_escalation_outbox_recovers_tickets_after_outage[asyncio] PASSED
tests/test_phase5_audit_and_escalation.py::test_t53_audit_tables_persist_redacted_trace_and_enforce_append_only PASSED
tests/test_phase5_audit_and_escalation.py::test_t54_admin_read_only_audit_trace_endpoint PASSED
tests/test_phase5_audit_and_escalation.py::test_t55_metrics_collector_computes_p50_p95_and_exports_json PASSED
```

- **Bộ kiểm thử Giai đoạn 5 (`tests/test_phase5_audit_and_escalation.py`)**: **5/5 bài kiểm thử đạt (100%)**.
- **Bản dựng giao diện người dùng (`npm run build`)**: **Thành công (2013 modules transformed)**.

