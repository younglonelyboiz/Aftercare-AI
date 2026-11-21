# EVIDENCE TUẦN 8 — TÍCH HỢP PORTAL BỆNH NHÂN VÀ NHÂN VIÊN

- **Dự án:** Aftercare-AI — hỗ trợ chăm sóc hen sau xuất viện
- **Milestone:** `Tuan8`
- **Tuần:** W08
- **Tag dự kiến:** `w08`, chưa tạo
- **Ngày lập hồ sơ:** 20/11/2026; cập nhật 21/11/2026 (Asia/Ho_Chi_Minh)

## 1. Mục tiêu

Kiểm chứng hai portal và một luồng end-to-end từ patient chat cờ đỏ tới điều dưỡng xử lý ticket. Bộ evidence giữ một video dùng backend thật; các bài UI có API mock được giữ làm regression test và được nêu đúng phạm vi.

## 2. Hạng mục và trạng thái

| Hạng mục | Bằng chứng | Trạng thái |
|---|---|---|
| Patient dashboard → check-in PEF | `frontend/tests/ui/patient-portal.spec.js` | UI test đạt; API mock |
| Patient dashboard → HOPI chat | `frontend/tests/ui/patient-portal.spec.js` | UI test đạt; API mock |
| Nurse xem, tiếp nhận, ghi biên bản và resolve | `frontend/tests/ui/staff-portal-e2e.spec.js` | UI test đạt; API mock |
| Patient chat cờ đỏ → nurse resolve | `frontend/tests/ui/backend-live-e2e.spec.js`, `backend/app/testing/live_e2e.py`, [video 04](./demo-videos/04-live-backend-patient-to-nurse.webm) | Live E2E đạt; FastAPI, PostgreSQL và WebSocket thật |
| Giữ ticket sau acknowledge | `frontend/src/components/Nurse/LiveAlertBanner.jsx` | Hoàn tất trên PR #37; chờ review/merge |
| Backend regression | `tests/e2e/test_scenarios.py`, `tests/orchestration/test_invariants.py` | 11/11 đạt |

### Sửa lỗi UX trên nurse banner

Trước W08, banner chỉ chọn ticket `OPEN`; sau acknowledge ticket thành `ACKNOWLEDGED` nên banner biến mất và điều dưỡng mất đường mở biên bản. Thay đổi W08 giữ ticket chưa `RESOLVED` trên banner, ưu tiên ticket mới và chỉ hiện nút “Tiếp Nhận Ca” cho ticket `OPEN`.

## 3. Kịch bản live end-to-end

Một nurse watcher mở WebSocket. Trên trang được quay, patient đăng nhập và gửi triệu chứng cờ đỏ qua `/chat/chat`. Safety graph backend trả phản hồi an toàn, tạo ticket `P0_CRITICAL` trong PostgreSQL và phát `NEW_ALERT_TICKET` tới watcher. Trang quay chuyển tài khoản sang nurse, tải ticket qua API, acknowledge, nhập biên bản và resolve. Bài test đọc lịch sử ticket để xác nhận `RESOLVED` cùng resolution notes. [Video 04](./demo-videos/04-live-backend-patient-to-nurse.webm) là một recording liên tục dài 85,6 giây qua hai portal.

Bài live dùng schema PostgreSQL tên ngẫu nhiên riêng, tự xóa sau test; log ghi nhận 0 schema cùng tiền tố còn lại sau chạy. Nhánh cờ đỏ không cần gọi LLM ngoài. Kết quả này chỉ áp dụng cho môi trường thử nghiệm W08; chưa kiểm chứng đường check-in → cảnh báo với backend thật trong browser.

## 4. Kết quả định lượng

| Nhóm | Kết quả | Phạm vi |
|---|---:|---|
| Playwright UI regression | 3/3 đạt | Patient check-in, HOPI và nurse resolve; API mock |
| Playwright live backend E2E | 1/1 đạt | REST, PostgreSQL, WebSocket và persistence thật |
| Backend scenario + invariant | 11/11 đạt | 4 scenario + 7 invariant có sẵn; 4 warning Pydantic |
| Frontend production build | Đạt | Vite build thành công |
| Frontend lint | Hoàn tất, còn warning | Warning hiện có trong frontend |

Chi tiết lệnh và lần chạy: [test-results.txt](./test-results.txt); số liệu máy đọc được: [metrics.csv](./metrics.csv); sơ đồ: [end_to_end_flow.mmd](./figures/end_to_end_flow.mmd). Bài UI dùng mock chỉ chứng minh hành vi giao diện; bài live mới chứng minh tích hợp API và dữ liệu.

## 5. Issue, PR và reviewer

| Deliverable | Issue | PR | Reviewer | Trạng thái |
|---|---|---|---|---|
| Patient portal UI checks | [#34](https://github.com/younglonelyboiz/Aftercare-AI/issues/34) | [#36](https://github.com/younglonelyboiz/Aftercare-AI/pull/36) | Nguyễn Trường Giang | Đang review |
| Staff portal và live E2E | [#35](https://github.com/younglonelyboiz/Aftercare-AI/issues/35) | [#37](https://github.com/younglonelyboiz/Aftercare-AI/pull/37) | Nguyễn Trường Giang | Đang review |

PR #37 do tài khoản `younglonelyboiz` mở, base là nhánh patient để diff chỉ hiện staff/E2E. Sau khi PR #36 merge, đổi base PR #37 sang `main`. Tag `w08` chỉ tạo sau khi review và tích hợp.

## 6. Tái hiện và giới hạn

- UI regression: `cd frontend && npm run test:ui -- --grep 'patient overview|patient asks HOPI|nurse reviews' --reporter=line`.
- Live E2E: `cd frontend && npm run test:ui -- --config=playwright.backend.config.js --reporter=line`; cần PostgreSQL theo `.env`, quyền tạo/xóa schema tạm và browser Playwright.
- Backend regression: `pytest -q tests/e2e/test_scenarios.py tests/orchestration/test_invariants.py`.

Cần bổ sung test live cho check-in → cảnh báo, xem xét WebSocket reconnect/polling fallback và dọn warning lint. `manifest.json` ghi SHA-256 cho các tệp evidence và không tự băm chính nó.
