# W07 - Giai đoạn 1: Nền tảng Điều phối LangGraph (Orchestration Foundation)

**Nhánh:** `feat/w07-orchestration-foundation`
**Tài liệu thiết kế gốc:** [Agent_Orchestration_Guardrails_Design.md](../../docs/Agent_Orchestration_Guardrails_Design.md) — Mục 3, Mục 5 và Mục 6 (T1.1 đến T1.7)
**Kết quả kiểm thử:** `tests/test_phase1_orchestration.py` (22 bài kiểm thử), `tests/test_phase0_safety.py` (12 bài kiểm thử), `tests/test_safety/test_symptom_screener.py` (9 bài kiểm thử)

---

## 1. NỘI DUNG GỢI Ý CHO GITHUB ISSUE

```markdown
**Title:** [W07][Orchestration] Phase 1 — Xây dựng nền tảng đồ thị điều phối tất định bằng LangGraph StateGraph (T1.1 - T1.7)

### Bối cảnh
Triển khai Giai đoạn 1 trong thiết kế Agent Orchestration & Guardrails (docs/Agent_Orchestration_Guardrails_Design.md): chuyển luồng xử lý tuyến tính trong `AftercareRAGService` sang đồ thị trạng thái tất định `StateGraph` của LangGraph, cưỡng chế các bất biến an toàn (INV-1, INV-2, INV-4, INV-7) và tách cổng gọi mô hình ngôn ngữ lớn `LLMGateway`.

### Danh sách nhiệm vụ
- [ ] **T1.1:** Cập nhật `requirements.txt` với `langgraph>=0.2.0` và `pyyaml>=6.0.0`.
- [ ] **T1.2:** Định nghĩa `AftercareState`, `GuardEvent`, `RiskDowngradeError` và hàm `escalate_risk()` bảo đảm bất biến rủi ro đơn điệu tăng (INV-1).
- [ ] **T1.3:** Xây dựng decorator `@safe_node` đo độ trễ từng nút (`latency_ms`) và cưỡng chế Fail-closed khi nút gặp lỗi (INV-4).
- [ ] **T1.4:** Tách bộ mẫu phản hồi lâm sàng tiếng Việt sang `guardrails/templates_vi.py` và xây dựng các nút chuyên trách trong `orchestration/nodes/`.
- [ ] **T1.5:** Xây dựng các hàm định tuyến tất định trong `orchestration/routing.py` và biên dịch đồ thị `StateGraph` trong `orchestration/graph.py`; xuất sơ đồ Mermaid `Evidence/W07/figures/orchestration_graph.mmd`.
- [ ] **T1.6:** Chuyển `AftercareRAGService.process_chat` thành lớp mặt tiền (Facade) gọi đồ thị `StateGraph`, bổ sung `trace_id` và `guard_events` vào `ChatResponse` mà vẫn giữ nguyên tương thích ngược.
- [ ] **T1.7:** Tách `llm/gateway.py` (`LLMGateway`) quản lý chuỗi dự phòng OpenRouter -> Gemini, danh sách trắng mô hình, giới hạn thời gian chờ và đo độ trễ.

### Tiêu chí hoàn thành
- Mọi hành vi hạ mức rủi ro trong cùng một lượt xử lý đều ném `RiskDowngradeError` (INV-1).
- Nhánh `RED_ZONE`, `YELLOW_ZONE`, khóa phiên Cờ Đỏ, chặn chính sách và thiếu bằng chứng tuyệt đối không gọi LLM (INV-2).
- Lỗi bất ngờ tại bất kỳ nút nào đều chuyển về `safe_fallback` kèm `GuardEvent(decision="FALLBACK")` (INV-4).
- Đạt 100% bài kiểm thử Giai đoạn 1 và toàn bộ bài kiểm thử hồi quy Giai đoạn 0.
```

---

## 2. TÓM TẮT CÁC NHIỆM VỤ ĐÃ HOÀN THÀNH

| Mã nhiệm vụ | Nội dung thực hiện | Trạng thái | Tệp mã nguồn chính |
| :--- | :--- | :---: | :--- |
| **T1.1** | Khóa phiên bản `langgraph>=0.2.0` và bổ sung `pyyaml>=6.0.0` | Đã hoàn thành | `requirements.txt` |
| **T1.2** | Định nghĩa `AftercareState`, `GuardEvent`, `RiskDowngradeError` và hàm `escalate_risk()` (bất biến INV-1) | Đã hoàn thành | `backend/app/orchestration/state.py` |
| **T1.3** | Xây dựng decorator `@safe_node` bắt lỗi, đo `latency_ms` từng nút và chuyển hướng an toàn (bất biến INV-4) | Đã hoàn thành | `backend/app/orchestration/safe_node.py` |
| **T1.4** | Tách mẫu phản hồi tiếng Việt chuẩn và viết 12 nút chuyên trách cho đồ thị | Đã hoàn thành | `backend/app/guardrails/templates_vi.py`, `backend/app/orchestration/nodes/*` |
| **T1.5** | Viết bộ hàm định tuyến tất định `routing.py`, đồ thị `graph.py` và xuất sơ đồ `orchestration_graph.mmd` | Đã hoàn thành | `backend/app/orchestration/routing.py`, `backend/app/orchestration/graph.py` |
| **T1.6** | Chuyển `AftercareRAGService` sang gọi `StateGraph`, mở rộng `ChatResponse` thêm `trace_id` và `guard_events` | Đã hoàn thành | `backend/app/rag/service.py`, `backend/app/schemas/chat.py` |
| **T1.7** | Tách `LLMGateway` độc lập với chuỗi dự phòng OpenRouter sang Gemini, danh sách trắng mô hình và đo độ trễ | Đã hoàn thành | `backend/app/llm/gateway.py` |

---

## 3. CHI TIẾT KỸ THUẬT

### 3.1. Bất biến rủi ro đơn điệu (T1.2 — `orchestration/state.py`)
- Thứ tự mức độ rủi ro được cố định: `NORMAL (0) < YELLOW_ZONE (1) < RED_ZONE (2)`.
- Hàm `escalate_risk(current_level, new_level)` là cổng duy nhất để cập nhật `risk_level`. Nếu `new_level` thấp hơn `current_level`, hàm lập tức ném `RiskDowngradeError`.
- Hàm `make_initial_state()` sinh mã truy vết duy nhất `trace_id` (`trace-<12 ký tự hex>`) cho mỗi lượt hội thoại.

### 3.2. Bảo vệ nút theo nguyên tắc Fail-closed (T1.3 — `orchestration/safe_node.py`)
- Decorator `@safe_node(node_name, layer)` bọc mọi nút trong đồ thị:
  1. Đo thời gian thực thi bằng `time.perf_counter()` và ghi vào `state["latency_ms"][node_name]`.
  2. Cho phép các ngoại lệ nghiệp vụ có chủ đích (`PatientNotFoundError`, `RiskDowngradeError`) đi qua để tầng API hoặc bộ kiểm thử xử lý đúng ngữ nghĩa.
  3. Mọi ngoại lệ thời gian chạy khác đều bị bắt lại, ghi nhật ký lỗi kèm `trace_id`, bật `degraded = True`, gán `error = "<node>:<ExceptionType>"` và nối thêm `GuardEvent(decision="FALLBACK")` để hàm định tuyến chuyển ngay về nút `safe_fallback`.

### 3.3. Đồ thị điều phối tất định 12 nút (T1.4, T1.5 — `orchestration/graph.py` và `routing.py`)
Đồ thị `StateGraph(AftercareState)` gồm 12 nút:
1. `load_context`: nạp hồ sơ bệnh nhân từ mã bệnh nhân.
2. `sanitize_input`: chuẩn hóa Unicode NFC, loại bỏ ký tự điều khiển và giới hạn 2.000 ký tự.
3. `safety_triage`: chạy `SymptomScreenerEngine` trên văn bản gốc trước khi bị cắt ngắn.
4. `session_lock_check`: nếu phiên đang bị khóa ở chế độ Cờ Đỏ (`session_locked_red=True`), cưỡng chế nâng lên `RED_ZONE`.
5. `policy_guard`: điểm gắn bộ kiểm tra chính sách đầu vào (L2).
6. `retrieve_evidence`: truy xuất đoạn tài liệu y khoa và chuẩn hóa danh sách trích dẫn.
7. `generate_answer`: nút duy nhất được gọi `LLMGateway` (có kiểm tra khẳng định `risk_level` không thuộc Đỏ/Vàng ngay đầu hàm).
8. `output_guard`: điểm gắn bộ kiểm tra đầu ra (L5), hỗ trợ 3 quyết định `PASS`, `FAIL` (về `safe_fallback`) và `RISK_UP` (nâng lên `action_plan_response`).
9. `emergency_response`, `action_plan_response`, `safe_refusal`, `no_evidence_response`, `safe_fallback`: 5 nút phản hồi tất định từ mẫu soạn sẵn trong `guardrails/templates_vi.py`.
10. `finalize` và `audit`: điểm hội tụ bắt buộc của mọi nhánh trước khi kết thúc (`END`).

### 3.4. Cổng LLM tập trung và Facade tương thích ngược (T1.6, T1.7)
- `LLMGateway` (`backend/app/llm/gateway.py`) đóng gói toàn bộ kết nối OpenRouter và Google Gemini SDK, kiểm tra danh sách trắng mô hình (`resolve_model`), giới hạn thời gian chờ và trả về đối tượng `LLMCallResult(text, provider, model, latency_ms, succeeded)`.
- `AftercareRAGService` (`backend/app/rag/service.py`) khởi tạo `self.graph` và thực thi `self.graph.invoke(initial_state)` trong `process_chat()`, trả về thêm `trace_id`, `guard_events` và `latency_ms` trong khi vẫn giữ nguyên mọi thuộc tính và chữ ký hàm mà Giai đoạn 0 đang sử dụng.

---

## 4. DANH SÁCH TỆP THAY ĐỔI VÀ TẠO MỚI

```text
M  requirements.txt
M  backend/app/rag/service.py
M  backend/app/schemas/chat.py
A  backend/app/guardrails/__init__.py
A  backend/app/guardrails/templates_vi.py
A  backend/app/llm/__init__.py
A  backend/app/llm/gateway.py
A  backend/app/orchestration/__init__.py
A  backend/app/orchestration/state.py
A  backend/app/orchestration/safe_node.py
A  backend/app/orchestration/routing.py
A  backend/app/orchestration/graph.py
A  backend/app/orchestration/nodes/__init__.py
A  backend/app/orchestration/nodes/context.py
A  backend/app/orchestration/nodes/sanitize.py
A  backend/app/orchestration/nodes/triage.py
A  backend/app/orchestration/nodes/policy_guard.py
A  backend/app/orchestration/nodes/responders.py
A  backend/app/orchestration/nodes/retrieve.py
A  backend/app/orchestration/nodes/generate.py
A  backend/app/orchestration/nodes/output_guard.py
A  backend/app/orchestration/nodes/finalize_audit.py
A  Evidence/W07/figures/orchestration_graph.mmd
A  Evidence/W07/W07_Phase1_Orchestration_Foundation.md
A  tests/test_phase1_orchestration.py
```

**Câu lệnh commit gợi ý:**

```text
feat(orchestration): W07 phase 1 - LangGraph deterministic state graph and LLM gateway (closes #<số_issue>)
```

