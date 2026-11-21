# Video W08: patient → nurse với backend thật

[04-live-backend-patient-to-nurse.webm](./04-live-backend-patient-to-nurse.webm) là recording liên tục dài 83,8 giây. Bệnh nhân đăng nhập, gửi triệu chứng cờ đỏ qua API thật; sau khi chuyển tài khoản, điều dưỡng xem ticket, tiếp nhận, ghi biên bản và resolve. Một nurse watcher riêng xác nhận sự kiện WebSocket realtime.

Bài test dùng FastAPI và PostgreSQL trong schema kiểm thử riêng. Xem [README W08](../README.md) và `frontend/tests/ui/backend-live-e2e.spec.js` để biết phạm vi và cách tái tạo.
