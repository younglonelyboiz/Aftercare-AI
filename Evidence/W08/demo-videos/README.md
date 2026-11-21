# Video demo W08

Các clip được quay bằng Playwright trên giao diện web ở độ phân giải desktop. Video không có thuyết minh âm thanh. Ba video đầu dùng API mock; video 04 gọi backend thật và ghi vào PostgreSQL trong schema kiểm thử riêng, schema này tự xóa khi server kiểm thử dừng.

| Tệp | Luồng |
|---|---|
| `01-patient-dashboard-checkin.webm` | Bệnh nhân xem tổng quan, nhập PEF và gửi check-in. |
| `02-patient-hopi-chat.webm` | Bệnh nhân mở HOPI, gửi câu hỏi và xem phản hồi. |
| `03-nurse-alert-resolution.webm` | Điều dưỡng xem ticket chatbot, tiếp nhận, ghi biên bản và đóng ticket. |
| `04-live-backend-patient-to-nurse.webm` | Một recording liên tục dài 85.6 giây, có khoảng dừng để đọc: bệnh nhân đăng nhập và chat cờ đỏ → đăng xuất/chuyển sang portal điều dưỡng → xem ticket, tiếp nhận, ghi biên bản và resolve. Backend/API/PostgreSQL thật; nurse watcher riêng xác nhận sự kiện WebSocket realtime. |

Tái tạo video mock: `cd frontend && npm run test:ui -- --grep 'demo video|nurse reviews'`.

Tái tạo backend live (cần PostgreSQL theo `.env`, quyền tạo/xóa schema tạm và browser Playwright): `cd frontend && npm run test:ui -- --config=playwright.backend.config.js --reporter=line`.
