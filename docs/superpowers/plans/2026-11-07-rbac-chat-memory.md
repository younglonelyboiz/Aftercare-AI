# RBAC, đăng nhập demo và bộ nhớ chatbot

Người dùng giao tự quyết chi tiết và triển khai trực tiếp ngày 07/11/2026. Native implementation, dùng React/FastAPI/PostgreSQL hiện có. Thiết kế lại FE tổng thể được hoãn.

## Quyết định

- Ba vai trò admin, nurse, patient. Backend xác thực bằng phiên opaque trong cookie HttpOnly, token chỉ lưu hash trong DB, hết hạn và thu hồi khi đăng xuất/vô hiệu hóa tài khoản. Mật khẩu PBKDF2 có salt.
- Demo được bật riêng bằng DEMO_LOGIN_ENABLED; mặc định tắt. Chọn nhanh tài khoản demo do server liệt kê, không cho client tự khai role. Tài khoản thường đăng nhập bằng username/password.
- Admin quản lý người dùng và phân công nurse; nurse truy cập bệnh nhân được phân công; patient chỉ bệnh nhân gắn tài khoản. Kiểm tra trên REST, quyền sở hữu reminder/ticket/conversation và WebSocket. Kết quả tổng hợp cũng được lọc.
- Không nhận actor/role từ frontend để quyết định quyền. Thao tác ticket ghi tên tài khoản đăng nhập.
- Hội thoại lưu theo patient_id và owner_user_id. Người tạo mới được gửi tin hoặc xóa. Admin/nurse được phép đọc các hội thoại bệnh nhân trong phạm vi chăm sóc, không gửi giả danh chủ hội thoại.
- Ngắn hạn: 12 tin gần nhất, ngân sách ký tự và tóm tắt trích xuất các lượt cũ, tất cả tải từ DB.
- Dài hạn: lưu nguyên hội thoại và các ghi chú trích nguyên văn lời người dùng, có thời điểm, nguồn message/conversation và nhãn chưa xác minh. Truy hồi các ghi chú liên quan từ hội thoại trước, chỉ trong cùng bệnh nhân và chủ hội thoại. Cho phép xem/xóa memory. Không dùng lời kể làm đơn thuốc hay tự sửa hồ sơ.
- Prompt có hồ sơ JSON nền, care plan và check-in gần nhất từ DB, short-term và long-term như dữ liệu tham khảo tách biệt với chỉ dẫn hệ thống. Triage quy tắc vẫn ưu tiên; lưu cả lượt đỏ/vàng. LLM và retriever lazy-load để test/khởi động không nạp model hai lần.
- FE thêm login với chọn nhanh role/tài khoản; admin có quản lý tài khoản và phân công; nurse/patient không chuyển thành vai trò khác. Chat tải lịch sử, tạo phiên mới, xem/xóa ghi nhớ và reset state khi đổi người/patient. Không lưu token trong localStorage.

## Công việc

1. Models: auth users/sessions/nurse assignments và conversations/messages/memory notes, migration/seed idempotent riêng, không xóa dữ liệu cũ.
2. Auth service/dependencies, login/logout/me/demo endpoints, admin user management; test 401/403, expiry, token revoke, CSRF và last-admin guard.
3. RBAC trên API hiện có, lọc patient lists/overview/tickets và hạn chế WebSocket theo phân công; test IDOR và thao tác chéo bệnh nhân.
4. Memory service + conversation API, LLM prompt/history/clinical context, concurrency và giới hạn nội dung; test memory qua phiên và restart service, tách chủ hội thoại, delete/forget, rollback khi LLM lỗi.
5. Login/admin/chat UI + credentialed axios; kiểm tra chuyển account, patient không thấy nurse/admin, mở lại lịch sử và chat memory.
6. Test database tách biệt, không chạy fixture W06 xóa production. Build/lint, browser checks desktop/mobile và kiểm tra runtime local. Review độc lập và sửa lỗi trước hoàn thành.

## Kiểm chứng

Tests chạy SQLite tạm cho auth và memory dùng JSON ORM portable; integration PostgreSQL schema tạm cho row locks/scoping. Stub LLM/retriever để kiểm tra prompt và memory không phụ thuộc API trả phí. Smoke test thật trên HTTP/WebSocket local cho đăng nhập, quyền và history. Kiểm tra cold start/restart và schema idempotency. Cập nhật hướng dẫn chạy, demo users và giới hạn (demo-only login, trích xuất memory chưa phải clinical fact verification).
