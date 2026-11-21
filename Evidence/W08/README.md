# BÁO CÁO EVIDENCE TUẦN 8 — TÍCH HỢP PORTAL BỆNH NHÂN VÀ NHÂN VIÊN

- **Dự án:** Aftercare-AI — hỗ trợ chăm sóc hen sau xuất viện
- **Milestone:** `Tuan8`
- **Tuần:** W08
- **Tag dự kiến:** `w08` — chưa tạo vì các thay đổi tuần 8 chưa được chốt thành commit cuối tuần.
- **Ngày lập hồ sơ:** 20/11/2026 (Asia/Ho_Chi_Minh)

## 1. Mục tiêu tuần

Kiểm chứng khả năng sử dụng liền mạch các portal bệnh nhân và nhân viên, tập trung vào check-in, trao đổi với HOPI và xử lý cảnh báo tại nurse station. Đóng gói kết quả thành số liệu, test log, sơ đồ luồng và video demo có thể phát lại.

## 2. Hạng mục và trạng thái

| Hạng mục | Kết quả | Tệp / mã nguồn liên quan | Trạng thái |
|---|---|---|---|
| Bệnh nhân xem dashboard và gửi check-in | Playwright thao tác tổng quan, nhập PEF, gửi check-in; video đã quay | `frontend/tests/ui/demo-videos.spec.js`, `demo-videos/01-patient-dashboard-checkin.webm` | Hoàn tất, API mock |
| Bệnh nhân mở HOPI và gửi câu hỏi | Playwright mở chat, gửi câu hỏi và nhận phản hồi; video đã quay | `frontend/tests/ui/demo-videos.spec.js`, `demo-videos/02-patient-hopi-chat.webm` | Hoàn tất, API mock |
| Điều dưỡng nhận và đóng cảnh báo | Thêm UI E2E; tiếp nhận ticket, nhập biên bản và resolve; video đã quay | `frontend/tests/ui/staff-portal-e2e.spec.js`, `demo-videos/03-nurse-alert-resolution.webm` | Hoàn tất, API mock |
| Video E2E đầy đủ: bệnh nhân → điều dưỡng | Một clip quay liền mạch portal bệnh nhân gửi chat, đăng xuất/chuyển tài khoản sang điều dưỡng, thấy cảnh báo, tiếp nhận, ghi biên bản và resolve; watcher thứ hai xác minh WebSocket realtime | `frontend/tests/ui/backend-live-e2e.spec.js`, `backend/app/testing/live_e2e.py`, `demo-videos/04-live-backend-patient-to-nurse.webm` | Hoàn tất, PostgreSQL schema cô lập |
| Giữ ticket sau khi điều dưỡng tiếp nhận | Sửa banner để ticket `ACKNOWLEDGED` tiếp tục xuất hiện với thao tác xử lý; ẩn nút tiếp nhận lặp lại | `frontend/src/components/Nurse/LiveAlertBanner.jsx` | Hoàn tất |
| Regression backend | Chạy 4 scenario lâm sàng và 7 invariant hiện có | `tests/e2e/test_scenarios.py`, `tests/orchestration/test_invariants.py` | 11/11 đạt |
| Build và lint frontend | Production build đạt; lint chạy xong, còn warning | frontend | Build đạt; lint cần dọn warning |

### 2.1. Sự cố UX phát hiện và xử lý

Trước thay đổi, `LiveAlertBanner` chỉ chọn ticket trạng thái `OPEN`. Khi điều dưỡng tiếp nhận, backend chuyển ticket sang `ACKNOWLEDGED`; banner biến mất, làm mất đường thao tác mở biên bản giải quyết. W08 điều chỉnh thứ tự chọn ticket để vẫn hiển thị cảnh báo chưa `RESOLVED`, ưu tiên ticket `OPEN`, và chỉ hiện nút “Tiếp Nhận Ca” khi trạng thái còn `OPEN`. Luồng UI test xác nhận điều dưỡng tiếp tục được tới bước resolve.

## 3. Kịch bản kiểm thử

### UI demo (Playwright)

1. **Patient dashboard → check-in:** mở tổng quan, chuyển sang Check-in, nhập PEF và lưu.
2. **Patient → HOPI:** mở trợ lý, gửi câu hỏi và xem phản hồi.
3. **Staff → alert resolution:** xem cảnh báo chatbot, tiếp nhận, ghi biên bản can thiệp và đóng ticket.

Ba clip đầu route API tới response giả lập, chỉ chứng minh UI. Clip 04 chạy frontend và API thật qua HTTP/WebSocket, dùng PostgreSQL đang cấu hình nhưng tạo một schema tên ngẫu nhiên riêng rồi xóa schema đó khi test kết thúc; không ghi vào các bảng/schema dữ liệu hiện có. Bài test dùng tài khoản test và dữ liệu bệnh nhân mẫu trong repo. Luồng cờ đỏ đi qua safety graph backend thật (không mock API/orchestration); nhánh khẩn cấp không cần gọi LLM ngoài.

Kịch bản live E2E: nurse watcher đăng nhập và mở WebSocket → màn hình được quay đăng nhập patient, gửi triệu chứng cờ đỏ qua `/chat/chat` → backend lưu hội thoại và ticket `P0_CRITICAL` vào PostgreSQL → watcher nhận `NEW_ALERT_TICKET` thật → màn hình quay đăng xuất patient, đăng nhập nurse, tải ticket từ API → acknowledge → nhập biên bản và resolve → test đọc API lịch sử, xác nhận `RESOLVED` cùng resolution notes. Video 04 là một recording liên tục trên cùng trang qua hai portal; watcher chỉ dùng để kiểm chứng sự kiện WebSocket realtime trong lúc quay.

### Regression backend

- Kịch bản A: tư vấn vùng xanh có bằng chứng và trích dẫn.
- Kịch bản B: cờ đỏ cấp cứu, khóa phiên đến khi cảnh báo được xử lý.
- Kịch bản C: cơn hen vùng vàng và kế hoạch theo dõi.
- Kịch bản D: chặn ý định tự ngưng thuốc kiểm soát.
- Bảy invariant: nguy cơ không bị hạ cấp, không gọi LLM ở nhánh khẩn cấp/khóa, outbox khi lỗi, fail-closed, cổng bằng chứng, bảo vệ PII và audit trail.

Các bài backend này là regression suite có sẵn; trong W08 chúng được chạy lại để xác nhận các thay đổi portal không làm hỏng lớp orchestration.

## 4. Kết quả định lượng

| Nhóm kiểm chứng | Kết quả | Ghi chú |
|---|---:|---|
| Playwright demo UI | 3/3 đạt | Các endpoint được mock |
| Playwright live backend E2E | 1/1 đạt | PostgreSQL schema cô lập; REST + WebSocket + persistence thật |
| Backend scenario + invariant | 11/11 đạt | 4 scenario + 7 invariant; 4 cảnh báo deprecation Pydantic |
| Frontend production build | Đạt | Vite build thành công |
| Frontend lint | Hoàn tất, có warning | Warning import chưa dùng, dependency/effect và Unicode regex tồn tại trong frontend |

Dữ liệu máy đọc được nằm ở [`metrics.csv`](./metrics.csv); log lệnh ở [`test-results.txt`](./test-results.txt).

## 5. Video và sơ đồ

- [Patient dashboard và check-in](./demo-videos/01-patient-dashboard-checkin.webm)
- [HOPI chat](./demo-videos/02-patient-hopi-chat.webm)
- [Điều dưỡng xử lý cảnh báo](./demo-videos/03-nurse-alert-resolution.webm)
- [Video scenario đầy đủ: bệnh nhân gửi chat → điều dưỡng tiếp nhận và resolve](./demo-videos/04-live-backend-patient-to-nurse.webm)
- [Sơ đồ luồng tích hợp](./figures/end_to_end_flow.mmd)

> Video 01–03 là WebM không thuyết minh, API mock. Video 04 dài 85.6 giây, có dừng để đọc dashboard, phản hồi cờ đỏ, cảnh báo và biên bản; dùng backend và PostgreSQL thật trong schema kiểm thử cô lập, không dùng dữ liệu bệnh nhân thật hoặc sửa schema dữ liệu sẵn có.

## 6. Issue, PR, reviewer và tag

| Deliverable | Issue | PR | Reviewer | Trạng thái |
|---|---|---|---|---|
| Patient portal demo flows | [#34](https://github.com/younglonelyboiz/Aftercare-AI/issues/34) | [#36](https://github.com/younglonelyboiz/Aftercare-AI/pull/36) | Nguyễn Trường Giang (`giangjk250704`) | PR đang review |
| Nurse alert resolution UX và live E2E | [#35](https://github.com/younglonelyboiz/Aftercare-AI/issues/35) | [#37](https://github.com/younglonelyboiz/Aftercare-AI/pull/37) | Nguyễn Trường Giang (`giangjk250704`) | PR đang review |
| Backend regression verification | Thuộc regression suite W07 đã có | Không phải PR mới W08 | N/A | Chạy lại trong W08 |

PR staff được mở bằng tài khoản `younglonelyboiz` và giao cho Giang review, vì GitHub không cho tác giả tự review. PR này nối tiếp PR patient để diff review tách rõ phần việc. `main` tại lúc tách nhánh là `ccd24e8` (merge PR #33). Tag `w08` là nhãn dự kiến, chưa tạo trước khi hai PR được review và tích hợp.

## 7. Hạn chế và việc tiếp theo

- Đã có bài kiểm thử tích hợp Patient API → PostgreSQL ticket → Nurse WebSocket/UI, hiện bao phủ luồng chat cờ đỏ; check-in → cảnh báo vẫn chưa được kiểm chứng live trong browser.
- Test live tự tạo/xóa schema PostgreSQL riêng; xác nhận log test và quyền CREATE/DROP SCHEMA trước khi chạy ở môi trường khác.
- Dọn các warning lint có ảnh hưởng tới nurse portal; bổ sung kiểm tra reconnect/polling fallback cho WebSocket khi chuẩn bị chạy nhiều instance.
- Sau review: cập nhật PR staff về `main` khi PR patient được merge; kiểm tra lại evidence, tạo commit cuối tuần rồi mới gắn tag `w08`.

## 8. Cấu trúc thư mục

```text
Evidence/W08/
├── README.md
├── metrics.csv
├── test-results.txt
├── figures/
│   └── end_to_end_flow.mmd
├── demo-videos/
│   ├── README.md
│   ├── 01-patient-dashboard-checkin.webm
│   ├── 02-patient-hopi-chat.webm
│   ├── 03-nurse-alert-resolution.webm
│   └── 04-live-backend-patient-to-nurse.webm
└── manifest.json
```

`manifest.json` chứa metadata và SHA-256 của từng evidence file (manifest không tự băm chính nó).
