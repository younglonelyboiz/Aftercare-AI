# Đăng nhập, phân quyền và memory chatbot

## Chạy bản demo local

1. Chạy migration một lần (chạy lại không ghi đè tài khoản hay hội thoại):
   ```bash
   venv/bin/python -m backend.app.db.migrate_identity_memory --demo
   ```
2. Trong `.env`, đặt `DEMO_LOGIN_ENABLED=true`; khởi động lại BE.
3. Mở http://localhost:5173, chọn Bệnh nhân / Điều dưỡng / Quản trị viên, rồi chọn tài khoản mẫu.

Tài khoản mẫu: `admin.demo`, `nurse.demo`, `patient1.demo`, `patient2.demo`, `patient3.demo`. Mật khẩu ban đầu được tạo ngẫu nhiên; dùng nút chọn nhanh để demo. Admin có thể tạo tài khoản thường với mật khẩu riêng trong trang Quản trị. Demo login chỉ cho phép tài khoản có cờ `is_demo`; gửi role từ client không thay đổi quyền.

Ngoài chế độ demo: đặt `DEMO_LOGIN_ENABLED=false`, dùng biến môi trường `BOOTSTRAP_ADMIN_PASSWORD` (ít nhất 10 ký tự) khi chạy migration không có `--demo` để tạo admin ban đầu nếu chưa có admin. Tài khoản mặc định có tên `admin`. Khi phục vụ qua HTTPS, đặt `COOKIE_SECURE=true` và cấu hình `CORS_ORIGINS` đúng địa chỉ FE.

## Quyền

| Chức năng | Admin | Nurse | Patient |
|---|---|---|---|
| Quản lý tài khoản, vai trò, phân công | Có | Không | Không |
| Hồ sơ, check-in, nhắc nhở | Toàn bộ | Bệnh nhân được phân công | Chỉ hồ sơ gắn với tài khoản |
| Cập nhật care plan | Có | Bệnh nhân được phân công | Không |
| Vé cảnh báo, WebSocket | Toàn bộ | Chỉ bệnh nhân được phân công | Không |
| Quét quá hạn thủ công | Toàn bộ | Phạm vi được phân công | Không |
| Reset dữ liệu demo | Có | Không | Không |
| Chat và memory riêng | Có | Có, trong phạm vi chăm sóc | Có, hồ sơ của mình |

Backend kiểm tra quyền ở mọi endpoint; việc ẩn nút ở FE chỉ hỗ trợ trải nghiệm. Các thao tác vé ghi danh tính từ tài khoản đăng nhập. Admin/nurse có thể đọc một hội thoại trong phạm vi chăm sóc qua API nhưng không gửi hoặc xóa giả danh chủ hội thoại. API danh sách hội thoại và ghi nhớ mặc định chỉ trả dữ liệu của người đang đăng nhập.

Phiên đăng nhập dùng token opaque 256-bit trong cookie HttpOnly/SameSite=Lax; DB chỉ lưu hash. Mặc định phiên hết hạn sau 8 giờ. Đăng xuất, khóa tài khoản, đổi role, đổi liên kết bệnh nhân hoặc mật khẩu thu hồi phiên; WebSocket kiểm tra lại phiên/quyền khi gửi dữ liệu và heartbeat. Mật khẩu PBKDF2-SHA256 600.000 vòng và salt riêng. Đăng nhập mật khẩu có giới hạn 5 lần sai/15 phút theo username. Kiểm tra Origin và Sec-Fetch-Site cho thao tác trình duyệt.

## Bộ nhớ chatbot

- **Ngắn hạn:** tải tối đa 12 tin gần nhất từ DB, tối đa 18.000 ký tự; đính kèm bản tóm tắt trích xuất các câu người dùng đã nói ở lượt cũ (tối đa 6.000 ký tự). Không phụ thuộc React state hoặc RAM backend.
- **Dài hạn:** giữ nguyên lịch sử hội thoại trong PostgreSQL; lưu ghi chú nguyên văn lời người dùng (tối đa 1.500 ký tự/ghi chú), có nguồn message/conversation và thời điểm, nhãn `user_reported`. Mỗi lượt truy hồi tối đa 6 ghi chú từ 200 ghi chú gần nhất theo từ khóa và thời gian, cùng patient và cùng chủ hội thoại. Không sử dụng vector/embedding cho memory trong phiên bản này.
- **Ngữ cảnh chăm sóc:** tải care plan đang hoạt động, thuốc trong plan, check-in mới nhất và cảnh báo còn mở; thông tin hiện hành ưu tiên hơn hồ sơ JSON nền và lời kể chưa xác minh.
- LLM nhận system prompt riêng, các lượt user/assistant đúng vai trò và dữ liệu memory có nhãn. Câu hỏi nối tiếp bổ sung hai câu user gần nhất vào truy vấn RAG tài liệu. Luồng đỏ/vàng vẫn dùng quy tắc có sẵn, được lưu vào lịch sử.
- Khóa hàng hội thoại trong PostgreSQL giúp hai yêu cầu gửi đồng thời giữ đúng thứ tự; chỉ commit cả cặp user/assistant sau khi có trả lời. Lỗi provider trả 503, không lưu lượt dở dang.
- FE tự mở hội thoại gần nhất, cho chọn lịch sử, tạo cuộc trò chuyện mới, xem/xóa ghi nhớ và xóa hội thoại. Đổi tài khoản/bệnh nhân sẽ tạo state chat riêng. Tạo cuộc trò chuyện mới vẫn có thể truy hồi ghi nhớ dài hạn của chính tài khoản cho bệnh nhân đó.

**Ý nghĩa của xóa:** “Xóa ghi nhớ” chỉ xóa ghi chú dùng cho truy hồi dài hạn; tin nhắn và tóm tắt hội thoại vẫn tồn tại. Muốn xóa cả lịch sử và các ghi chú phát sinh, dùng “Xóa cuộc trò chuyện”. Không có thao tác tự sửa đơn thuốc/hồ sơ từ memory.

Memory hiện là trích xuất nguyên văn và truy hồi từ khóa, chưa phải tóm tắt ngữ nghĩa bằng LLM hay thông tin lâm sàng đã xác nhận. Các benchmark provider được giả lập trong test để đo chính xác việc truyền ngữ cảnh mà không gọi API trả phí.

## API

- `GET /api/v1/auth/demo-accounts`, `POST /auth/demo-login`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`.
- `GET/POST /api/v1/admin/users`, `PATCH /admin/users/{id}`, `PUT /admin/users/{id}/assignments`.
- `GET/POST /api/v1/chat/conversations`, `GET/DELETE /chat/conversations/{id}`. Đọc tin cũ bằng `?before=<sequence>`; mỗi trang tối đa 100 tin.
- `POST /api/v1/chat/chat`: `{patient_id, message, conversation_id?}`; trả `conversation_id` và `message_id` cùng phản hồi/trích dẫn.
- `GET /api/v1/chat/memory?patient_id=...`, `DELETE /chat/memory/{id}`.

## Kiểm thử

```bash
venv/bin/python -m pytest tests -q
# Chỉ tạo/xóa schema tạm riêng; không xóa dữ liệu trong public schema:
AFTERCARE_TEST_POSTGRES=1 venv/bin/python -m pytest tests/test_auth_memory.py -q
cd frontend
npm run build
npm run lint
```

W06 đã được chuyển sang SQLite tạm và đăng nhập test riêng, không còn xóa vé database local khi chạy test. Test gửi tin đồng thời chỉ chạy trong lượt PostgreSQL. Mã khởi động BE không tự migration/seed để tránh ghi đè ngoài ý muốn.

Kết quả W06 trong test mặc định ghi vào thư mục tạm để không thay đổi gói minh chứng đã nghiệm thu. Muốn xuất lại minh chứng có chủ đích: `W06_EVIDENCE_DIR=Evidence/W06 venv/bin/python -m pytest tests/test_escalation_w06.py -q` (bộ test mới dùng SQLite tạm).

Giao diện ghi nhớ hiển thị tối đa 100 ghi chú gần nhất. Những ghi chú cũ hơn vẫn nằm trong DB và được xóa khi xóa hội thoại nguồn; bản hiện tại chưa có phân trang quản lý toàn bộ memory.
