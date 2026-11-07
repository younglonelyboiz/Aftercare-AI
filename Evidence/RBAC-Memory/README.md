# Kiểm chứng RBAC và chat memory — 07/11/2026

- Toàn bộ test: **37 passed, 1 skipped**. Test concurrency bỏ qua ở SQLite đã chạy riêng trên PostgreSQL.
- PostgreSQL integration: **24 passed**, schema tạm riêng, bao gồm gửi đồng thời, login/thu hồi phiên, phân công, IDOR, history/memory và lưu lượt cảnh báo đỏ.
- Frontend build đạt; lint không có lỗi, còn các cảnh báo được lưu nguyên trong frontend-lint.txt.
- Trình duyệt Chromium: chọn nhanh ba vai trò, chặn truy cập sai quyền, cookie qua reload, dashboard nurse/admin và login mobile 390 px không tràn ngang; không ghi nhận lỗi JavaScript.
- Đã rà soát độc lập; ba vấn đề về thuốc cũ, lọc ticket trước LIMIT và alert khi đổi bệnh nhân đã sửa và kiểm tra lại.

## Tệp

- `verification.json`, `browser-checks.json`: kết quả tổng hợp.
- `unit-and-regression-tests.txt`, `postgres-integration-tests.txt`: đầu ra pytest.
- `frontend-build.txt`, `frontend-lint.txt`: kiểm tra FE.
- `login-desktop.png`, `login-mobile.png`, `patient-chat.png`, `nurse-dashboard.png`, `admin-users.png`: ảnh chụp thực tế localhost.

Provider LLM được giả lập trong test để kiểm tra chính xác ngữ cảnh gửi và rollback; luồng quy tắc cảnh báo đỏ chạy mã thật. Memory dài hạn là ghi chú trích nguyên văn + truy hồi từ khóa, chưa dùng embedding. Hướng dẫn sử dụng: `docs/RBAC_AND_CHAT_MEMORY.md`.
