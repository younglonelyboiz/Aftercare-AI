# W07 · Giai đoạn 0 — Vá lỗ hổng an toàn khẩn cấp (Phase 0 Safety Gaps)

**Nhánh:** `fix/w07-phase0-safety-gaps` (tách từ `feat/w06-frontend-alerts`)
**Tài liệu thiết kế gốc:** [Agent_Orchestration_Guardrails_Design.md](./Agent_Orchestration_Guardrails_Design.md) — Mục 1.2 (G1, G2, G7, G10) và Mục 6 (T0.1 → T0.4)
**Kết quả kiểm thử:** `tests/test_phase0_safety.py` — **12/12 passed**; hồi quy `tests/test_safety` — **9/9 passed**


```markdown
**Title:** [W07][Safety] Phase 0 — Chat Red/Yellow không tạo AlertTicket, LLM lỗi lộ thông báo kỹ thuật, chat chặn event loop

### Bối cảnh
Rà soát code cho thiết kế Agent Orchestration & Guardrails (docs/Agent_Orchestration_Guardrails_Design.md) phát hiện 4 lỗ hổng vi phạm nguyên tắc Zero-Silent Failure và Fail-safe.

### Lỗi
- [ ] **T0.1 (G1 – Nghiêm trọng):** `/api/v1/chat/chat` phát hiện RED_ZONE/YELLOW_ZONE nhưng KHÔNG tạo AlertTicket → trạm điều dưỡng không nhận được cảnh báo.
- [ ] **T0.2 (G2 – Nghiêm trọng):** Khi OpenRouter/Gemini lỗi, bệnh nhân nhận chuỗi lỗi kỹ thuật ("Lỗi xử lý phản hồi từ OpenRouter…"); exception khác trả HTTP 500 kèm chi tiết nội bộ.
- [ ] **T0.3 (G7):** `process_chat` (đồng bộ, gọi embedding/rerank/LLM) chạy trực tiếp trong `async def` → chặn event loop, làm trễ WebSocket cảnh báo điều dưỡng.
- [ ] **T0.4 (G10):** `model_override` không có whitelist.

### Tiêu chí hoàn thành
- Chat RED → vé `P0_CRITICAL` + sự kiện WS `NEW_ALERT_TICKET`; chat YELLOW → vé `P1_HIGH`; LLM không được gọi.
- Tạo vé thất bại không chặn phản hồi cấp cứu cho bệnh nhân.
- Không còn chuỗi lỗi kỹ thuật nào hiển thị cho bệnh nhân; trả thông điệp an toàn có nhắc gọi 115.
- Khi LLM chậm, các endpoint async khác vẫn phản hồi < 0,5 s.
- model_override ngoài whitelist bị bỏ qua.
```

---

## 2. TÓM TẮT THAY ĐỔI

| Task | Lỗ hổng | Trạng thái | File chính |
| :--- | :--- | :---: | :--- |
| **T0.1** | Chat Đỏ/Vàng không tạo AlertTicket | Đã sửa | `api/v1/endpoints/chat.py`, `clinical_agents/triage_agent.py`, `rag/service.py`, `schemas/chat.py` |
| **T0.2** | Lộ lỗi kỹ thuật cho bệnh nhân khi LLM/hệ thống lỗi | Đã sửa | `rag/service.py`, `rag/safe_messages.py` *(mới)*, `api/v1/endpoints/chat.py`, `core/config.py` |
| **T0.3** | Chat đồng bộ chặn event loop | Đã sửa | `api/v1/endpoints/chat.py` |
| **T0.4** | `model_override` không có whitelist | Đã sửa | `core/config.py`, `rag/service.py` |
| — | Bộ kiểm thử Giai đoạn 0 | Mới | `tests/test_phase0_safety.py` *(mới)* |

---

## 3. CHI TIẾT TỪNG THAY ĐỔI

### 3.1. T0.1 — Chat Vùng Đỏ/Vàng tự động tạo AlertTicket

**Trước:** `process_chat()` trả về template cấp cứu rồi `return` ngay. Không có vé, không có WebSocket → điều dưỡng không hề biết bệnh nhân vừa nhắn *"tôi không thở được"*.

**Sau:**

1. `TriageAgent.evaluate_full_text()` *(mới)* trả về `ScreenerResult` đầy đủ (cờ + lý do lâm sàng) thay vì chỉ chuỗi mức rủi ro.
2. `process_chat()` trả thêm trường nội bộ `screener = {matched_flags, matched_reasons}`. Trường này **bị lọc khỏi phản hồi API** bởi `response_model=ChatResponse`.
3. `chat_endpoint` gọi hàm mới `escalate_chat_result()`, dùng lại `EscalationService.create_or_escalate_ticket()` có sẵn (debounce 5 phút + broadcast WebSocket):

| `safety_status` | `priority` | `alert_type` (mới) |
| :--- | :--- | :--- |
| `RED_ZONE` | `P0_CRITICAL` | `CHAT_RED_FLAG_DETECTION` |
| `YELLOW_ZONE` | `P1_HIGH` | `CHAT_YELLOW_ZONE_ALERT` |
| `NORMAL` | — | không tạo vé |

4. `clinical_data` của vé gồm: `source="CHAT"`, `matched_flags`, `matched_reasons`, `message_excerpt` (tối đa 500 ký tự).
5. **Non-blocking:** nếu tạo vé lỗi (ví dụ DB mất kết nối), lỗi được ghi log mức `CRITICAL`, bệnh nhân **vẫn nhận đủ hướng dẫn cấp cứu**, `escalation_ticket_id = null`.
6. `ChatResponse` thêm trường tùy chọn `escalation_ticket_id` (tương thích ngược, frontend không cần sửa).
7. Template Đỏ/Vàng thêm dòng xác nhận *"Hệ thống đã gửi báo động khẩn cấp đến điều dưỡng trực."* / *"Điều dưỡng phụ trách đã được thông báo để theo dõi."*
8. Khôi phục cách đọc hồ sơ an toàn bằng `.get()` + hướng dẫn mặc định khi hồ sơ thiếu `action_plan_rules`. Bản trong working tree trước đó dùng `profile["action_plan_rules"]`, sẽ gây `KeyError` (HTTP 500) với hồ sơ thiếu trường này đúng vào lúc bệnh nhân đang cấp cứu.

> [!NOTE]
> Cột `alert_type` là `String(50)`, hai giá trị mới (23 và 22 ký tự) không cần migration. Nurse Command Center hiện không lọc theo `alert_type`, nên vé từ chat hiển thị ngay. Việc gắn nhãn “Nguồn: Chatbot” trên UI thuộc T5.1.

### 3.2. T0.2 — Fail-safe: không lộ lỗi kỹ thuật cho bệnh nhân

**Trước:** `_call_llm()` trả về chuỗi như `"Lỗi xử lý phản hồi từ OpenRouter (openai/gpt-4o): <exception>"`, và chuỗi này được hiển thị nguyên văn cho bệnh nhân. Exception khác trong endpoint trả HTTP 500 với `detail` chứa thông tin nội bộ (có thể lộ cả lỗi DB hoặc khóa API).

**Sau:**

- File mới `backend/app/rag/safe_messages.py` chứa `SAFE_FALLBACK_MESSAGE`: báo hệ thống chưa trả lời được, **nhắc các dấu hiệu cần gọi 115**, gợi ý liên hệ điều dưỡng, kèm disclaimer y tế.
- `_call_llm()` giờ trả về `Optional[str]`: `None` khi mọi nhà cung cấp lỗi hoặc trả nội dung rỗng. Chi tiết lỗi **chỉ ghi vào log** (`logger.exception`).
- Chuỗi dự phòng: model override (nếu hợp lệ) → OpenRouter → Gemini → `None`. Nội dung rỗng/chỉ khoảng trắng cũng được coi là lỗi.
- `process_chat()`: khi LLM trả `None`/rỗng thì trả `SAFE_FALLBACK_MESSAGE` với `degraded = true` và `citations = []`.
- `chat_endpoint`: exception không lường trước → HTTP 200 + `SAFE_FALLBACK_MESSAGE` + `degraded = true` (không còn 500 lộ chi tiết). Bệnh nhân không tồn tại vẫn trả **404** như cũ.
- Thêm timeout cho LLM: `LLM_TIMEOUT_SECONDS` (mặc định 20 s), OpenRouter `max_retries=1`, Gemini `http_options.timeout` (tự lùi về client mặc định nếu SDK không hỗ trợ).
- `ChatResponse` thêm trường `degraded: bool = False` để frontend/giám sát nhận biết phản hồi dự phòng.

### 3.3. T0.3 — Không chặn event loop

**Trước:** `async def chat_endpoint` gọi trực tiếp `rag_service.process_chat(...)` (đồng bộ: embedding BGE-M3, reranker, HTTP tới LLM). Trong suốt thời gian chờ LLM, mọi tác vụ async khác trên cùng worker đều bị treo, gồm cả WebSocket `/ws/nurse-alerts`, broadcast cảnh báo P0 và `NonResponseWorker`.

**Sau:** dùng `await run_in_threadpool(rag_service.process_chat, ...)`, đẩy pipeline đồng bộ sang threadpool.

**Kiểm chứng:** test giả lập LLM chậm 1,5 s; một endpoint async khác gọi song song phải phản hồi < 0,5 s → **đạt**.

### 3.4. T0.4 — Whitelist model LLM

- `ChatRequest` vốn **không** có `model_override` (đã có test khẳng định điều này), nhưng `process_chat`/`_call_llm` vẫn nhận tham số này từ code nội bộ và script đánh giá.
- Thêm `ALLOWED_LLM_MODELS` (biến môi trường, phân tách bằng dấu phẩy) và property `settings.allowed_llm_models` (luôn gồm `OPENROUTER_MODEL` và `GEMINI_MODEL`).
- `_resolve_model()` bỏ qua override không nằm trong whitelist và ghi log cảnh báo.

**Biến môi trường mới (tùy chọn, `.env`):**

```dotenv
# Danh sách model bổ sung được phép override (ngoài OPENROUTER_MODEL, GEMINI_MODEL)
ALLOWED_LLM_MODELS=google/gemini-2.5-flash,anthropic/claude-3.5-sonnet
# Timeout mỗi lần gọi LLM (giây)
LLM_TIMEOUT_SECONDS=20
```

---

## 4. HỢP ĐỒNG API SAU THAY ĐỔI

`POST /api/v1/chat/chat`: request **không đổi**. Response thêm 2 trường tùy chọn:

```json
{
  "response": "CẢNH BÁO CỜ ĐỎ CẤP CỨU: ...\n\nHệ thống đã gửi báo động khẩn cấp đến điều dưỡng trực.",
  "safety_status": "RED_ZONE",
  "citations": [],
  "degraded": false,
  "escalation_ticket_id": "ticket-3f9a1c2b7d4e"
}
```

Sự kiện WebSocket gửi tới Nurse Station (định dạng sẵn có của W06):

```json
{
  "event": "NEW_ALERT_TICKET",
  "ticket": {
    "priority": "P0_CRITICAL",
    "alert_type": "CHAT_RED_FLAG_DETECTION",
    "trigger_reason": "Phát hiện qua Chatbot: ...",
    "clinical_data": { "source": "CHAT", "matched_flags": ["..."], "message_excerpt": "..." }
  }
}
```

---

## 5. KIỂM THỬ

**Chạy:**

```powershell
venv\Scripts\python.exe -m pytest tests\test_phase0_safety.py -v
```

Bộ test **không cần** PostgreSQL, GPU hay API key: retriever, LLM và EscalationService được giả lập.

| # | Test | Task | Kết quả |
| :-: | :--- | :---: | :---: |
| 1 | `test_t01_red_chat_creates_p0_ticket_and_never_calls_llm` | T0.1 | Đạt |
| 2 | `test_t01_yellow_chat_creates_p1_ticket` | T0.1 | Đạt |
| 3 | `test_t01_normal_chat_creates_no_ticket` | T0.1 | Đạt |
| 4 | `test_t01_ticket_failure_does_not_block_emergency_response` | T0.1 | Đạt |
| 5 | `test_t01_profile_without_action_plan_does_not_crash` | T0.1 | Đạt |
| 6 | `test_t02_all_llm_providers_fail_returns_safe_fallback` | T0.2 | Đạt |
| 7 | `test_t02_empty_llm_output_returns_safe_fallback` | T0.2 | Đạt |
| 8 | `test_t02_unexpected_exception_returns_safe_fallback_not_500` | T0.2 | Đạt |
| 9 | `test_t02_unknown_patient_still_404` | T0.2 | Đạt |
| 10 | `test_t03_slow_llm_does_not_block_event_loop` | T0.3 | Đạt |
| 11 | `test_t04_model_override_outside_whitelist_is_ignored` | T0.4 | Đạt |
| 12 | `test_t04_chat_request_does_not_expose_model_override` | T0.4 | Đạt |
| — | Hồi quy `tests/test_safety/test_symptom_screener.py` (9 test) | — | Đạt |

**Kiểm thử thủ công đề xuất (cần backend + DB chạy thật):**

1. Mở Nurse Command Center.
2. Ở widget chat bệnh nhân, gửi: *"Tôi không thở được, tím môi, xịt ventolin rồi không đỡ"*.
3. Kỳ vọng: chat hiện khối cấp cứu đỏ; Nurse Station hú còi + banner đỏ, có vé `CHAT_RED_FLAG_DETECTION`.
4. Gửi lại tin tương tự trong vòng 5 phút: vé được cập nhật, **không** tạo vé trùng (debounce).
5. Đặt `OPENROUTER_API_KEY` và `GEMINI_API_KEY` sai rồi hỏi một câu thường: nhận thông điệp an toàn, không có chữ "Lỗi…".

---

## 6. GIỚI HẠN CÒN LẠI (CHUYỂN SANG CÁC GIAI ĐOẠN SAU)

| Vấn đề | Lý do chưa xử lý | Giai đoạn |
| :--- | :--- | :---: |
| Khi exception xảy ra **trước** Safety Triage, hệ thống trả fallback với `safety_status="NORMAL"`. Thông điệp có nhắc 115 nhưng không tạo vé. | Cần cơ chế `@safe_node` và trạng thái `UNKNOWN` có cảnh báo riêng | T1.3 |
| Vé tạo lỗi khi DB mất kết nối chỉ được log, chưa có hàng đợi retry | Cần outbox pattern | T5.2 |
| Nurse Station chưa hiển thị nhãn “Nguồn: Chatbot” | Thay đổi UI | T5.1 |
| Chưa có Input/Output Guard (đổi liều, chẩn đoán, injection) | Phạm vi Giai đoạn 2 & 4 | Giai đoạn 2, Giai đoạn 4 |
| Chưa có khóa phiên sau ca Đỏ (session lock) | Cần bộ nhớ hội thoại | T3.6 |

---

## 7. DANH SÁCH FILE THAY ĐỔI

```text
M  backend/app/api/v1/endpoints/chat.py          # T0.1, T0.2, T0.3
M  backend/app/clinical_agents/triage_agent.py   # T0.1: evaluate_full_text()
M  backend/app/core/config.py                    # T0.2 timeout, T0.4 whitelist
M  backend/app/rag/service.py                    # T0.1, T0.2, T0.4
M  backend/app/schemas/chat.py                   # degraded, escalation_ticket_id
A  backend/app/rag/safe_messages.py              # T0.2: SAFE_FALLBACK_MESSAGE
A  tests/test_phase0_safety.py                   # 12 test
A  docs/W07_Phase0_Safety_Fixes.md               # tài liệu này
A  docs/Agent_Orchestration_Guardrails_Design.md # thiết kế tổng thể
```

**Commit message gợi ý** (thay `#<số>` bằng số issue sau khi tạo):

```text
fix(safety): W07 phase 0 - chat escalation, fail-safe LLM, non-blocking chat (closes #<số>)
```

