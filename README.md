# Aftercare-AI

# AI Agent hỗ trợ theo dõi và chăm sóc bệnh nhân sau xuất viện
## 1. Giới thiệu

Đề tài xây dựng một **AI Agent hỗ trợ theo dõi và chăm sóc bệnh nhân sau xuất viện** sử dụng dữ liệu mô phỏng.

Hệ thống hỗ trợ:

* Theo dõi kế hoạch chăm sóc sau xuất viện.
* Nhắc lịch uống thuốc và tái khám.
* Thực hiện check-in định kỳ.
* Phát hiện các tín hiệu nguy cơ dựa trên rule được định nghĩa.
* Chuyển tiếp các trường hợp cần xử lý cho nhân viên y tế.
* Trả lời câu hỏi dựa trên discharge plan và tài liệu được cho phép thông qua RAG.

> Hệ thống không chẩn đoán, không tự thay đổi điều trị và không thay thế nhân viên y tế.

---

## 2. Mục tiêu

* Mô hình hóa **care plan**, lịch thuốc, lịch tái khám và warning signs.
* Xây dựng workflow/state-machine cho AI Agent.
* Áp dụng **rule-based safety layer** trước và sau LLM.
* Xây dựng **RAG có citation** và giới hạn phạm vi trả lời.
* Xây dựng cơ chế **human-in-the-loop** và escalation.
* Ghi nhận các hoạt động quan trọng thông qua **audit log**.
* Đánh giá hệ thống bằng các safety test cases.

---

## 3. Phạm vi

Prototype chỉ sử dụng **dữ liệu giả lập**, không sử dụng PHI thật.

Phạm vi tập trung vào 1–2 kịch bản, ví dụ:

* Theo dõi bệnh nhân hậu phẫu đơn giản.
* Theo dõi bệnh nhân nội khoa ổn định sau xuất viện.

Hệ thống không:

* Chẩn đoán bệnh.
* Kê đơn hoặc thay đổi thuốc.
* Thay đổi phác đồ điều trị.
* Đưa ra khuyến cáo y khoa ngoài kế hoạch đã được bác sĩ phê duyệt.

---

## 4. Workflow

```text
Discharge Plan
      ↓
Care Plan
      ↓
Reminder / Check-in
      ↓
Patient Response
      ↓
Safety Rule
      ↓
   ┌───────────────┐
   │               │
Normal          Red Flag
   │               │
   ↓               ↓
Continue       Escalation
Monitoring         ↓
               Healthcare
                Staff
```

LLM được sử dụng để hỗ trợ xử lý ngôn ngữ và RAG, trong khi các quyết định safety quan trọng được kiểm soát bằng rule và human-in-the-loop.

---

## 5. RAG

RAG chỉ sử dụng:

* Discharge plan.
* Discharge instructions.
* Các tài liệu hướng dẫn công khai được lựa chọn.

Câu trả lời phải có **nguồn/citation** và không được vượt quá phạm vi tài liệu.

Khi không đủ thông tin, Agent không tự suy đoán.

---

## 6. Safety & Evaluation

Các nhóm test chính:

* Red flags.
* Missed escalation.
* Ambiguous input.
* Out-of-scope questions.
* Prompt injection.
* Unsupported medical advice.
* Citation accuracy.

Một số metric:

* Escalation Recall.
* Missed Escalation Rate.
* False Escalation Rate.
* Unsafe Response Rate.
* Citation Accuracy.
* Task Completion Rate.

---

## 7. Technology Stack

| Thành phần      | Công nghệ                   |
| --------------- | --------------------------- |
| Frontend        | Next.js                     |
| Backend         | FastAPI                     |
| Database        | PostgreSQL                  |
| Vector Database | pgvector / Qdrant           |
| Agent           | LangGraph                   |
| LLM             | LLM API / Local LLM         |
| Scheduler       | Celery / APScheduler / Cron |
| Deployment      | Docker                      |

---

## 8. Project Structure

```text
ai-post-discharge-agent/
├── apps/
│   ├── web/              # Next.js
│   └── api/              # FastAPI
│
├── agent/
│   ├── workflow/         # LangGraph
│   ├── safety/           # Safety rules
│   ├── rag/              # RAG pipeline
│   └── prompts/
│
├── data/
│   ├── synthetic/
│   └── test_cases/
│
├── tests/
│   ├── safety/
│   ├── agent/
│   └── rag/
│
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 9. Các giai đoạn thực hiện

1. Khảo sát bài toán và công nghệ.
2. Xây dựng synthetic dataset và test cases.
3. Thiết kế kiến trúc, database và API.
4. Xây dựng Agent workflow, RAG và safety layer.
5. Tích hợp hệ thống end-to-end.
6. Kiểm thử và đánh giá với các baseline.
7. Dockerize, tài liệu hóa và hoàn thiện báo cáo.

---

## 10. Kết quả mong đợi

Prototype có khả năng:

* Quản lý care plan sau xuất viện.
* Nhắc lịch và thực hiện check-in.
* Phát hiện nguy cơ theo rule.
* Escalate đến nhân viên y tế.
* Trả lời câu hỏi dựa trên RAG có citation.
* Kiểm soát các tình huống out-of-scope và prompt injection.
* Ghi lại audit log.
* Có bộ test và metric để đánh giá an toàn.

> **Lưu ý:** Đây là prototype phục vụ nghiên cứu/giáo dục, không phải hệ thống sử dụng trực tiếp trong chẩn đoán hoặc điều trị bệnh nhân.