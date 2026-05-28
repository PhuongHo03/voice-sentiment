# Tài liệu giải thích Frontend

## Mục đích

Thư mục `frontend/` chứa bảng điều khiển trực quan dành cho người dùng và quản trị viên, được xây dựng trên nền tảng **React + Vite + TypeScript**. Giao diện được tối ưu hóa toàn diện về cả thiết kế (dark mode, dynamic charts) và cấu trúc phần mềm (tách biệt hoàn toàn Business Logic khỏi UI Components nhờ hệ thống Custom Hooks).

Frontend cung cấp các chức năng:
- **Đăng ký & Đăng nhập**: Quản lý phiên đăng nhập an toàn, phân chia vai trò (Nhân viên / Admin).
- **Phân tích cuộc gọi (Personal Dashboard)**: Cho phép ghi âm microphone trực tiếp, tải file âm thanh hoặc gửi văn bản hội thoại để nhận diện giọng nói và phân tích cảm xúc cá nhân.
- **Thống kê cá nhân**: Hiển thị báo cáo hiệu suất, điểm đánh giá kỹ năng CSKH và xu hướng làm việc cá nhân.
- **Cổng Quản trị Admin (Admin Portal)**: Dành riêng cho tài khoản Quản trị viên duyệt kích hoạt thành viên mới, phân quyền vai trò, và theo dõi trực quan bảng xếp hạng, tiến độ xử lý và chi tiết từng cuộc gọi của toàn bộ nhân viên.

---

## Cấu trúc thư mục

Để đạt hiệu quả tối đa về khả năng mở rộng và bảo trì, dự án áp dụng mô hình phân tách vai trò:

```text
frontend/
├── src/app/App.tsx                     ← Khung xương bọc ngoài ứng dụng (App routing & Protected routes)
├── src/context/AuthContext.tsx         ← Quản lý phiên đăng nhập và đính kèm JWT token vào các API requests
├── src/pages/                          ← Các trang hiển thị chính (Pure Presentation Components)
│   ├── DashboardPage.tsx               ← Dashboard phân tích cảm xúc & thống kê của cá nhân
│   ├── AdminDashboardPage.tsx          ← Dashboard quản lý tiến độ nhân viên & duyệt tài khoản của Admin
│   ├── LoginPage.tsx                   ← Trang Đăng nhập tối giản trực quan
│   └── RegisterPage.tsx                ← Trang Đăng ký tài khoản mới
├── src/hooks/                          ← Nơi đóng gói toàn bộ logic nghiệp vụ (Custom Hooks)
│   ├── useAnalysis.ts                  ← Hook điều khiển luồng phân tích, polling và thống kê cá nhân
│   ├── useAdminDashboard.ts            ← Hook quản trị của Admin (đồng bộ URL, kích hoạt tài khoản, đổi vai trò)
│   ├── useLogin.ts                     ← Hook quản lý biểu mẫu đăng nhập và validation
│   ├── useRegister.ts                  ← Hook quản lý validation và đăng ký tài khoản
│   └── useAudioRecorder.ts             ← Hook quản lý luồng ghi âm từ microphone thông qua MediaRecorder
├── src/components/                     ← Các thành phần UI nhỏ dùng chung
│   ├── audio/AudioInputPanel.tsx       ← Panel xử lý kéo thả file ghi âm và nhập văn bản
│   ├── transcript/TranscriptLog.tsx    ← Nhật ký hội thoại chia luồng vai nói sinh động
│   ├── summary/SummaryCard.tsx         ← Thẻ tóm tắt các ý chính cuộc gọi
│   └── sentiment/SentimentBadge.tsx    ← Huy hiệu trạng thái cảm xúc động
├── src/services/analysisApi.ts         ← Trình gọi API kết nối trực tiếp đến API Gateway
├── src/styles/main.css                 ← Design system, CSS Variables (Teal/Rose/Blue/Violet), Glassmorphism
└── src/types/                          ← Định nghĩa kiểu dữ liệu tĩnh nghiêm ngặt
    ├── analysis.ts                     ← Kiểu dữ liệu phiên phân tích (JobStatus, SessionListItem...)
    └── admin.ts                        ← Kiểu dữ liệu quản trị (Employee, EmployeeStats, AccountUser)
```

---

## Kiến Trúc Tách Biệt Logic Nghiệp Vụ (Custom Hooks Separation)

Đây là điểm cải tiến quan trọng giúp mã nguồn frontend cực kỳ sạch sẽ và dễ bảo trì. Thay vì viết các biến trạng thái `useState`, hiệu ứng phụ `useEffect` hay các hàm xử lý sự kiện (event handlers) bên trong các tệp UI Pages, tất cả logic đã được tách biệt hoàn toàn vào thư mục `src/hooks/`.

### 1. Phân hệ Phân tích Cá nhân (`DashboardPage` & `useDashboardAnalysis`)
* **Tệp hiển thị**: `DashboardPage.tsx` chỉ còn khoảng 850 dòng (chủ yếu là cấu trúc HTML/CSS hiển thị giao diện, donut chart, scorecard). Trang này chỉ gọi và giải cấu trúc các thuộc tính trả về từ Hook:
  ```typescript
  const { sessions, activeSessionId, handleAudioSubmit, handleTextSubmit, ... } = useDashboardAnalysis(isAdmin);
  ```
* **Tệp Custom Hook**: `useAnalysis.ts` quản lý:
  * Tải danh sách lịch sử phiên phân tích khi khởi chạy.
  * Lắng nghe trạng thái và thực hiện cơ chế Polling (truy vấn lặp mỗi 2 giây) nếu phát hiện có phiên đang xử lý (`pending`/`processing`).
  * Thực thi các hàm đổi tên, xóa phiên, tải lên file ghi âm và nạp dữ liệu thống kê cá nhân.

### 2. Phân hệ Quản trị Admin (`AdminDashboardPage` & `useAdminDashboard`)
* **Tệp hiển thị**: `AdminDashboardPage.tsx` giảm mạnh từ gần 800 dòng xuống chỉ còn 440 dòng.
* **Tệp Custom Hook**: `useAdminDashboard.ts` đảm nhận toàn bộ các logic phức tạp:
  * Theo dõi sự kiện thay đổi lịch sử duyệt trình duyệt (`popstate`) để đồng bộ tab và lựa chọn nhân viên với thanh URL của trình duyệt (giúp lưu trạng thái khi nhấn Back/Forward).
  * Gọi API lấy danh sách nhân viên (`/api/admin/employees`) và toàn bộ tài khoản (`/api/admin/users`).
  * Gửi lệnh duyệt kích hoạt hoặc đổi quyền hạn tài khoản và kích hoạt Toast thông báo động.

### 3. Phân hệ Đăng nhập/Đăng ký
* **LoginPage** và **RegisterPage** chỉ xử lý hiển thị form và gán sự kiện.
* Toàn bộ việc kiểm tra regex định dạng email, so khớp mật khẩu xác nhận, quản lý trạng thái nút bấm `isSubmitting` và thông báo lỗi được đóng gói an toàn trong `useLogin.ts` và `useRegister.ts`.

---

## Quản lý Định tuyến & Bảo vệ (Routing & Protected Routes)

Mã nguồn `src/app/App.tsx` quản lý luồng phân phối giao diện dựa trên vai trò của tài khoản:
* **Khách vãng lai**: Chỉ được phép truy cập trang Đăng nhập / Đăng ký. Mọi nỗ lực truy cập sâu hơn đều bị tự động điều hướng (Redirect) về `/login`.
* **Nhân viên (Vai trò `employee`)**: Được cấp quyền truy cập đầy đủ vào **Dashboard Phân tích cá nhân** (`activeView = 'session'` hoặc `'dashboard'`). Mọi nỗ lực truy cập vào trang Admin đều bị chặn và cảnh báo.
* **Quản trị viên (Vai trò `admin`)**: Có toàn quyền chuyển đổi linh hoạt giữa **Dashboard cá nhân riêng** (thực hiện phân tích độc lập) và **Cổng Quản trị Admin** để xem báo cáo tiến độ chung.

---

## Thiết Kế Hệ Thống & CSS Cao Cấp (Aesthetics Design)

Giao diện áp dụng các tiêu chuẩn thiết kế cao cấp nhất hiện nay:
* **Harmonious Palette**: Sử dụng bảng màu phối hợp HSL độc quyền (Tím hoàng gia làm chủ đạo, Xanh Teal cho sắc thái tích cực, Hồng Rose cho sắc thái tiêu cực, và Xanh Dương cho trung lập).
* **Glassmorphism**: Áp dụng độ nhòe nền (`backdrop-filter: blur`), viền bán trong suốt (`rgba(255, 255, 255, 0.05)`) tạo cảm giác hiện đại, sang trọng.
* **Dynamic Animations**: Các biểu đồ SVG Donut Chart và Bar Chart vẽ hoàn toàn bằng mã động giúp các vòng tròn, thanh cột tự động co giãn và hiển thị dữ liệu mượt mà mà không cần nạp các thư viện nặng nề của bên thứ ba.

---

## Cấu Hình Mạng & Cổng Giao Tiếp (Network Configuration)

* **Master `.env` ở Root**: Biến cấu hình `VITE_API_BASE_URL` được nạp tập trung từ file `.env` ngoài root của dự án thông qua Docker Compose.
* **Bảo mật và CORS**: Cổng hoạt động Vite (`5173`) được bảo vệ hoàn toàn bên trong mạng nội bộ Docker. Reverse Proxy Nginx chạy ở cổng `9090` trên host đảm nhiệm việc tiếp nhận mọi yêu cầu tĩnh từ trình duyệt người dùng, tự động giải quyết triệt để lỗi chia sẻ tài nguyên nguồn gốc chéo (CORS) mà không cần cấu hình lỏng lẻo ở tầng API.
