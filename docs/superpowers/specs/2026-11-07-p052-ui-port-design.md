# Chuyển diện mạo p052 sang Aftercare-AI

Ngày: 07/11/2026. Trạng thái: chờ người dùng duyệt thiết kế.

## Ý định và quyết định đã thống nhất

Người dùng thích diện mạo `frontendp052` hơn frontend hiện tại, ngoại trừ trang đăng nhập. Đã chọn đưa giao diện p052 vào React + Vite hiện có và xác nhận muốn giữ sát diện mạo p052. Mục tiêu là chuyển giao diện thực tế, gồm bố cục, CSS, typography, icon, tài nguyên hình ảnh và trạng thái tương tác; không chỉ lấy cảm hứng hoặc đổi màu.

Nguồn chuẩn thị giác là mã `frontendp052`, không phải bản HTML phác thảo trong `.superpowers/brainstorm`. Phác thảo chỉ giúp trao đổi bố cục. Tài liệu này thay thế hướng thiết kế thị giác đang chờ duyệt trong `2026-11-07-patient-first-ui-design.md`; không thay đổi tài liệu RBAC/chat memory hay nghiệp vụ backend.

## Phạm vi và giới hạn

- Áp dụng cho toàn bộ giao diện sau đăng nhập: bệnh nhân, điều dưỡng, admin, chat, hộp thoại và thông báo của chức năng hiện có.
- Giữ giao diện và hành vi đăng nhập hiện tại, gồm đăng nhập mật khẩu, demo, kiểm tra phiên và đăng xuất.
- Giữ API, cookie HttpOnly, phân quyền và state theo tài khoản/bệnh nhân hiện có. Backend là nguồn quyết định quyền và kết quả lâm sàng.
- Giữ check-in hen, PEF, SpO₂, care plan, nhắc thuốc, lịch, cảnh báo, xác nhận an toàn, WebSocket và thao tác vé hiện có.
- Giữ lịch sử hội thoại, hội thoại mới, quản lý ghi nhớ, xóa hội thoại và trích dẫn/PDF của chatbot.
- Không chuyển nghiệp vụ hậu phẫu, ORANGE, ML, bàn giao ca, n8n, cuộc gọi hoặc API riêng của p052. Không mở rộng backend để làm cho mọi menu p052 hoạt động.
- Không thêm menu chết, số liệu giả hoặc tên bệnh nhân mặc định vào sản phẩm. Thiếu dữ liệu hiển thị trạng thái trống hoặc lỗi phù hợp.
- Giữ nguyên thư mục nguồn `frontendp052` làm tài liệu đối chiếu. Bảo toàn các thay đổi chưa commit hiện có trong workspace.

## Approaches — Các hướng đã cân nhắc

1. **Chuyển phần trình bày p052 vào React + Vite — người dùng chọn.** Giữ frontend đang nối backend, chuyển component và CSS nguồn sang nền hiện tại. Tốn công tách nghiệp vụ hậu phẫu khỏi giao diện nhưng giữ được các chức năng vừa phát triển.
2. **Dùng Next.js p052 làm frontend chính.** Ít chuyển đổi cấu trúc giao diện nguồn, nhưng phải nối lại API, auth, chat memory và các luồng hen. Phạm vi thay đổi lớn hơn, không được chọn.

## Chuẩn thị giác

Chuyển class và cấu trúc trình bày trực tiếp từ component nguồn khi có thể. Giữ tỉ lệ khối, độ rộng nội dung, nhịp khoảng cách, border, radius, shadow, teal/slate/mint, cỡ chữ, font weight, vị trí icon và trạng thái hover/focus/disabled/loading. Giữ responsive desktop/mobile theo nguồn, điều chỉnh ở nơi dữ liệu hen dài hoặc khác cấu trúc.

Nguồn chính: `app/globals.css`, `app/layout.tsx`, `components/patient/*`, `components/nurse-sidebar.tsx`, `app/nurse/dashboard/page.tsx`, `app/admin/dashboard/page.tsx`, `components/chat-widget.tsx` và các modal liên quan.

Font nguồn là Plus Jakarta Sans và JetBrains Mono. Đề xuất kỹ thuật: đưa font vào Vite qua tài nguyên font phù hợp, ưu tiên self-host nếu có sẵn; giữ đủ ký tự tiếng Việt. Dùng ảnh/mascot nguồn khi có, đổi nội dung “Khoa Ngoại Tổng Hợp” và hậu phẫu sang chăm sóc hen. Không phát sinh hình ảnh AI thay thế tài nguyên nguồn.

Thay đổi cần thiết vì nghiệp vụ/quyền không phải sai khác thị giác: bớt menu không hỗ trợ, thay trường hậu phẫu bằng trường hen, thêm điều khiển history/memory theo cùng kiểu component nguồn, giữ reset chỉ cho admin theo quyền hiện tại.

## Ánh xạ màn hình

| Khu vực | Diện mạo lấy từ p052 | Chức năng và dữ liệu Aftercare-AI |
|---|---|---|
| Bệnh nhân | Header, thẻ tóm tắt, tab desktop, bottom navigation mobile, bố cục form và thẻ thuốc | Hôm nay: check-in PEF/SpO₂/triệu chứng, care plan và reminders; Nhật ký: lịch/check-in; Hồ sơ: thông tin bệnh nhân hiện có |
| Chat | Cửa sổ/khung chat, màu mint, avatar, bubble, ô nhập và nút gửi | Chat API hiện tại, conversation_id, chọn/tạo/xóa hội thoại, xem/xóa memory, trích dẫn và PDF |
| Điều dưỡng | Sidebar, header, danh sách và khung chi tiết, badge, modal và bố cục dashboard | Bệnh nhân trong phạm vi được phân công, biểu đồ PEF, care plan editor, cảnh báo đang mở/lịch sử vé, tiếp nhận/hoàn tất, quét quá hạn |
| Admin | Header, thẻ, bảng/danh sách, form và nút của dashboard admin | Tạo tài khoản, đổi vai trò/liên kết bệnh nhân, khóa/mở khóa, phân công điều dưỡng và reset demo theo hành vi hiện tại |

Admin vẫn truy cập các portal hiện được cấp quyền; không biến switch portal thành quyền truy cập tự do cho bệnh nhân/điều dưỡng. Sidebar chỉ có đích đến thật. Các chỉ số tổng quan chỉ hiển thị nếu tính được chính xác từ dữ liệu hiện có và có nhãn đúng phạm vi.

Cảnh báo nguy cấp tiếp tục thấy được khi đổi tab; giữ nội dung, mức độ và luồng xử lý hiện có. Dùng chữ/icon cùng màu trạng thái, không chỉ dựa vào màu. Không thay ngưỡng hay tự tính lại phân tầng từ p052.

## Kiến trúc chuyển đổi — đề xuất của người triển khai

- Giữ JavaScript/JSX và Vite; chuyển các component TSX cần dùng sang JSX thay vì di chuyển toàn dự án sang TypeScript.
- Thêm Tailwind vào Vite để giữ class gốc p052. Giới hạn nguồn quét vào frontend thực tế; cô lập/reset CSS để không tác động `.auth-shell` và trang đăng nhập. Không sao chép nguyên global CSS gây thay đổi login.
- Tạo wrapper/theme dành riêng cho giao diện đã đăng nhập; giữ font và CSS login hiện tại. Tách style admin đang dùng chung `auth.css` khi cần.
- Thay `next/image`, `next/link`, `next/navigation`, `next/font` bằng cơ chế tương đương của Vite/React. Giữ cơ chế chuyển portal/tab hiện có, không đưa router mới chỉ để mô phỏng đường dẫn p052.
- Dùng `frontend/src/services/api.js` làm lớp API chuẩn. Không mang `frontendp052/lib/api.ts`, token JS-cookie hay dữ liệu mặc định từ dự án cũ sang.
- Giữ logic tải/lưu, xử lý lỗi và kiểm soát quyền của frontend hiện tại; tách thành hook/component khi cần để gắn với view mới. Không mount đồng thời hai view mobile/desktop có side effect gây gửi trùng request hoặc mở hai WebSocket.
- Chuyển tài nguyên cần dùng vào `frontend/public`; không lấy cả build output hoặc node_modules của dự án nguồn.
- State chat phải tách theo user/patient như hiện tại; đổi tài khoản hoặc bệnh nhân không rò dữ liệu hội thoại. Chuyển tab trình bày không tự xóa form đang nhập hoặc tạo hội thoại mới.

## Trạng thái, responsive và khả năng thao tác

Mỗi vùng tải dữ liệu có loading, empty, error và retry phù hợp. Chỉ báo thành công sau API thành công; ngăn gửi trùng khi đang lưu. Phiên hết hạn dùng cơ chế hiện tại. Modal có tên truy cập, focus và thao tác đóng bằng bàn phím; nút icon có nhãn.

Đối chiếu ở desktop 1440px và mobile 390px, kiểm tra thêm 768px cho tablet. Không tràn ngang toàn trang; bảng có vùng cuộn riêng nếu cần. Bottom nav, chat và bàn phím không che nút lưu, thông báo hay cảnh báo. Tôn trọng reduced motion.

## Kiểm chứng và tiêu chí nghiệm thu

1. Chụp giao diện p052 ở cùng viewport để làm mốc thị giác; nếu nguồn không chạy với backend hiện tại, dùng dữ liệu fixture chỉ trong môi trường preview, không trộn vào sản phẩm. Ghi rõ phần nào mới chỉ đối chiếu mã nguồn.
2. So sánh ảnh trước/sau theo từng portal, chat và modal đại diện: cấu trúc, typography, màu, khoảng cách, icon, asset, trạng thái và responsive bám nguồn. Các khác biệt phải giải thích được bằng nghiệp vụ hen/quyền hoặc chức năng hiện tại.
3. Trang đăng nhập không đổi về bố cục, font, màu và hành vi; kiểm tra cả desktop/mobile sau khi Tailwind được tích hợp.
4. Chạy build/lint frontend; ghi nhận baseline để phân biệt lỗi tồn tại trước với lỗi phát sinh.
5. Kiểm chứng luồng bệnh nhân: login, check-in, lịch sử, care plan, nhắc thuốc, cảnh báo/xác nhận an toàn; luồng nurse: danh sách được phân công, chi tiết, sửa plan, WebSocket và xử lý vé; luồng admin: tạo/sửa/khóa tài khoản và phân công. Dùng DB/test data cô lập cho thao tác ghi, không reset dữ liệu thật để thử.
6. Kiểm chứng chat: gửi/tải lại lịch sử, đổi hội thoại, memory, xóa, trích dẫn/PDF, đổi user/patient và phiên hết hạn. Không làm mất hành vi RBAC/memory đang có.
7. Dùng kiểm thử sẵn có và bổ sung kiểm thử hồi quy cho thay đổi luồng/state có rủi ro; không viết test chỉ để khẳng định class CSS.

## Phần để người triển khai quyết định

Tên/chia nhỏ component, tổ chức CSS, cơ chế nạp font và bộ kiểm thử cụ thể được quyết định khi lập kế hoạch. Mọi chức năng p052 cần backend mới nằm ngoài phạm vi này. Nếu không thể giữ một chi tiết quan trọng của diện mạo nguồn, báo rõ trước khi thay bằng thiết kế khác.

Đây là một đợt chuyển giao diện nhiều màn hình. Sau khi người dùng duyệt tài liệu, bước tiếp theo là skill `writing-plans` để lập kế hoạch triển khai; chưa viết mã sản phẩm ở giai đoạn thiết kế.
