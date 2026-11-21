# EVIDENCE TUẦN 8 — PORTAL BỆNH NHÂN VÀ ĐIỀU DƯỠNG

- **Dự án:** Aftercare-AI — hỗ trợ chăm sóc hen sau xuất viện
- **Milestone:** `Tuan8`; **tag `w08`:** chưa tạo
- **Ngày lập:** 20/11/2026; **cập nhật:** 21/11/2026 (Asia/Ho_Chi_Minh)

## Mục tiêu và phân công

| Thành viên | Phạm vi được giao | Issue / PR | Kết quả hiện có |
|---|---|---|---|
| Hoàng Ngọc Đức | Portal bệnh nhân: đăng nhập, check-in PEF, HOPI; fixture FastAPI và PostgreSQL cô lập cho test live | [#34](https://github.com/younglonelyboiz/Aftercare-AI/issues/34) / [#36](https://github.com/younglonelyboiz/Aftercare-AI/pull/36) | Bài patient live 1/1 đạt; chờ review |
| Nguyễn Trường Giang | Portal điều dưỡng: theo dõi ticket, acknowledge, ghi biên bản, resolve; rà soát kịch bản patient → nurse | [#35](https://github.com/younglonelyboiz/Aftercare-AI/issues/35) / [#37](https://github.com/younglonelyboiz/Aftercare-AI/pull/37) | Bài full live 1/1 đạt; chờ review |

PR #37 và commit hiện được mở/ghi bằng tài khoản `younglonelyboiz`; bảng trên là **phân công**, không phải xác nhận Giang đã tác giả commit. Giang được yêu cầu review hai PR; GitHub không cho Đức tự review PR do mình mở.

## Hai kịch bản kiểm chứng bằng API thật

1. **Patient portal:** Playwright đăng nhập patient bằng demo login thật, gửi check-in PEF 465 qua `/care-tracker/checkin/`, xác nhận `GREEN`, đọc lại lịch sử từ PostgreSQL; sau đó gửi nội dung cờ đỏ qua HOPI `/chat/chat`, xác nhận `RED_ZONE` và đường gọi 115. File: `frontend/tests/ui/patient-portal.spec.js`.
2. **Patient → nurse:** Một nurse watcher mở WebSocket. Patient gửi chat cờ đỏ; backend tạo ticket P0 trong PostgreSQL, phát `NEW_ALERT_TICKET`. Trang quay chuyển sang nurse, acknowledge, ghi biên bản, resolve; bài test đọc ticket history để xác nhận `RESOLVED` và resolution notes. File: `frontend/tests/ui/backend-live-e2e.spec.js`; [video 04](./demo-videos/04-live-backend-patient-to-nurse.webm) là recording liên tục dài khoảng 83,8 giây.

Không có route API hoặc WebSocket mock trong hai bài W08 trên. Fixture `backend/app/testing/live_e2e.py` tạo schema PostgreSQL tên ngẫu nhiên riêng và xóa sau test. Nhánh chat cờ đỏ dùng safety graph thật, không cần gọi LLM ngoài.

## Kết quả

| Bài kiểm tra | Kết quả | Thời điểm |
|---|---:|---|
| Patient check-in + HOPI live | 1/1 đạt | 21/11/2026 |
| Patient → nurse live E2E | 1/1 đạt | 21/11/2026 |
| Backend scenario + invariant có sẵn | 11/11 đạt, 4 warning | 20/11/2026 |
| Frontend production build | Đạt | 20/11/2026 |
| Frontend lint | Hoàn tất, còn warning | 20/11/2026 |

Xem [test-results.txt](./test-results.txt), [metrics.csv](./metrics.csv), [manifest.json](./manifest.json) và [sơ đồ luồng](./figures/end_to_end_flow.mmd). Video chỉ minh chứng kịch bản chat cờ đỏ → nurse; đường check-in → cảnh báo chưa được quay hoặc kiểm chứng live trong browser.

## Tái hiện

- Patient live: `cd frontend && npm run test:ui -- --config=playwright.patient-live.config.js --reporter=line`.
- Patient → nurse live: `cd frontend && npm run test:ui -- --config=playwright.backend.config.js --reporter=line`.
- Backend regression: `pytest -q tests/e2e/test_scenarios.py tests/orchestration/test_invariants.py`.

Cần PostgreSQL theo `.env`, quyền CREATE/DROP SCHEMA tạm và browser Playwright. PR #37 dựa trên nhánh patient để diff chỉ gồm phần staff/E2E; sau khi PR #36 merge, đổi base PR #37 sang `main`. Tag `w08` chỉ tạo sau khi review và tích hợp.
