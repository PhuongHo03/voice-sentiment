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

Để đạt hiệu quả tối đa về khả năng mở rộng và bảo trì, dự án áp dụng mô hình phân tách theo tính năng (feature-based):

```text
frontend/
├── src/app/App.tsx                                      ← Khung xương bọc ngoài ứng dụng (App routing & Protected routes)
├── src/features/auth/                                   ← Phân hệ đăng nhập, đăng ký và phiên người dùng
│   ├── screens/LoginPage.tsx                            ← Trang Đăng nhập tối giản trực quan
│   ├── screens/RegisterPage.tsx                         ← Trang Đăng ký tài khoản mới
│   ├── hooks/useLogin.ts                                ← Hook quản lý biểu mẫu đăng nhập và validation
│   ├── hooks/useRegister.ts                             ← Hook quản lý validation và đăng ký tài khoản
│   ├── api/authApi.ts                                   ← Hàm gọi API đăng nhập, đăng ký và lấy hồ sơ hiện tại
│   ├── dtos/authDto.ts                                  ← Builder request payload và parser response/error auth
│   ├── states/AuthContext.tsx                           ← Quản lý phiên đăng nhập và token JWT
│   ├── types/auth.ts                                    ← Kiểu dữ liệu auth (User, Role, AuthContextType)
│   └── components/                                      ← UI trình bày chung của màn hình auth
├── src/features/analysis/                               ← Phân hệ phân tích cuộc gọi cá nhân
│   ├── screens/DashboardPage.tsx                        ← Dashboard phân tích cảm xúc & thống kê của cá nhân
│   ├── hooks/useAnalysis.ts                             ← Hook điều khiển luồng phân tích, polling và thống kê cá nhân
│   ├── hooks/useAudioRecorder.ts                        ← Hook quản lý luồng ghi âm microphone qua MediaRecorder
│   ├── api/analysisApi.ts                               ← Trình gọi API kết nối trực tiếp đến API Gateway
│   ├── dtos/analysisDto.ts                              ← Builder request payload và parser response phân tích/file
│   ├── states/analysisState.ts                          ← Type/view/storage helpers cho session/dashboard/files
│   ├── types/analysis.ts                                ← Kiểu dữ liệu phiên phân tích (JobStatus, SessionListItem...)
│   └── components/                                      ← UI chỉ dùng trong phân hệ phân tích
│       ├── audio/AudioInputPanel.tsx                    ← Panel kéo thả file ghi âm và nhập văn bản
│       ├── transcript/TranscriptLog.tsx                 ← Nhật ký hội thoại chia luồng vai nói sinh động
│       ├── summary/SummaryCard.tsx                      ← Thẻ tóm tắt các ý chính cuộc gọi
│       └── sentiment/SentimentBadge.tsx                 ← Huy hiệu trạng thái cảm xúc động
├── src/features/admin/                                  ← Phân hệ quản trị tiến độ nhân viên và duyệt tài khoản
│   ├── screens/AdminDashboardPage.tsx                   ← Dashboard quản lý tiến độ nhân viên & duyệt tài khoản
│   ├── hooks/useAdminDashboard.ts                       ← Hook quản trị (đồng bộ URL, kích hoạt tài khoản, đổi vai trò)
│   ├── api/adminApi.ts                                  ← Hàm gọi API nhân viên, tài khoản và phân quyền admin
│   ├── hooks/useObservabilityMetrics.ts                 ← Hook tải metrics hệ thống, trạng thái target và auto-refresh
│   ├── dtos/adminDto.ts                                 ← Builder request payload và parser response admin
│   ├── states/adminState.ts                             ← Type/tab/toast và helper đồng bộ URL state của Admin
│   ├── types/admin.ts                                   ← Kiểu dữ liệu quản trị (Employee, EmployeeStats, AccountUser)
│   ├── types/metrics.ts                                 ← Kiểu dữ liệu metrics từ Prometheus cho admin dashboard
│   └── components/                                      ← UI trình bày riêng của Admin
│       ├── AdminToast.tsx                               ← Toast thông báo trạng thái thao tác admin
│       ├── AdminHeader.tsx                              ← Header và nút chuyển/đăng xuất admin
│       ├── AdminTabs.tsx                                ← Điều hướng tab tiến độ/tài khoản/metrics hệ thống
│       ├── AdminPerformanceDashboard.tsx                ← Dashboard tiến độ nhân viên
│       ├── AdminObservabilityDashboard.tsx              ← Dashboard Prometheus metrics cho admin
│       └── AdminAccountManagement.tsx                   ← Bảng quản lý tài khoản hệ thống
└── src/styles/main.css                                  ← Design system, CSS Variables, Glassmorphism
```

---

## Kiến Trúc Tách Biệt Theo Tính Năng (Feature-Based Separation)

Mỗi phân hệ sở hữu màn hình, hook, API/state, component và kiểu dữ liệu của riêng nó. Luồng mặc định là `App.tsx → feature screen → feature hook → feature api/state/types → feature components`. Root-level chỉ giữ entrypoint, app shell và style dùng chung.

### 1. Phân hệ Phân tích Cá nhân (`features/analysis`)
* **Tệp hiển thị**: `screens/DashboardPage.tsx` chỉ lắp ghép giao diện dashboard, sidebar lịch sử, file manager, chart và scorecard.
* **Tệp Custom Hook**: `hooks/useAnalysis.ts` quản lý:
  * Tải danh sách lịch sử phiên phân tích khi khởi chạy.
  * Lắng nghe trạng thái và thực hiện cơ chế Polling (truy vấn lặp mỗi 2 giây) nếu phát hiện có phiên đang xử lý (`pending`/`processing`).
  * **Cơ chế xử lý lỗi Polling (404 Bug Fix)**: Nếu phiên phân tích được lưu trữ trong local state hoặc `localStorage` không còn tồn tại trên máy chủ (ví dụ: do database reset hoặc bị xóa), API sẽ phản hồi lỗi `404 Not Found`. Hook sẽ chủ động phát hiện lỗi này, dọn dẹp ID phiên lỗi khỏi `localStorage` và cập nhật trạng thái phiên trong React state sang `failed` để chấm dứt chu kỳ gọi API lặp vô hạn gây quá tải.
  * Thực thi các hàm đổi tên, xóa phiên, tải lên file ghi âm và nạp dữ liệu thống kê cá nhân.
* **API/DTO/State/Types/Components**: `api/analysisApi.ts`, `dtos/analysisDto.ts`, `states/analysisState.ts`, `types/analysis.ts` và `components/*` nằm cùng phân hệ để tránh rải business logic phân tích ra root.

### 2. Phân hệ Quản trị Admin (`features/admin`)
* **Tệp hiển thị**: `screens/AdminDashboardPage.tsx` giữ `useAdminDashboard`, tính toán KPI/donut và lắp ghép các component trình bày trong `components/`.
* **Tệp Custom Hook**: `hooks/useAdminDashboard.ts` đảm nhận toàn bộ các logic phức tạp:
  * Theo dõi sự kiện thay đổi lịch sử duyệt trình duyệt (`popstate`) để đồng bộ tab và lựa chọn nhân viên với thanh URL của trình duyệt (giúp lưu trạng thái khi nhấn Back/Forward).
  * Gọi `api/adminApi.ts` để lấy danh sách nhân viên (`/api/admin/employees`) và toàn bộ tài khoản (`/api/admin/users`).
  * Dùng `dtos/adminDto.ts` để build payload cập nhật trạng thái/vai trò và parse response trước khi đưa dữ liệu về hook.
  * Dùng `states/adminState.ts` cho type tab/toast và helper tính toán đường dẫn URL theo trạng thái Admin.
  * Gửi lệnh duyệt kích hoạt hoặc đổi quyền hạn tài khoản thông qua API module và kích hoạt Toast thông báo động.
* **Components**: `AdminToast`, `AdminHeader`, `AdminTabs`, `AdminPerformanceDashboard`, `AdminObservabilityDashboard`, `AdminAccountManagement` chỉ nhận props từ screen và render giao diện Admin; logic nghiệp vụ vẫn nằm trong hook.
* **Metrics tab**: đường dẫn `/admin/metrics` hiển thị metrics tổng hợp từ Prometheus. Frontend gọi API `/api/admin/metrics` trên Backend (được bảo vệ bằng admin session, cache 10s trên Redis), đảm bảo Prometheus API không bị phơi bày ra ngoài. Trang gồm khung tổng quan, khung 9 thẻ target health (frontend được đại diện qua Nginx) và một khung metrics tổng hợp theo thứ tự Targets online, Voice jobs, LLM jobs, Request rate, 5xx rate, API P95, MinIO storage used, Postgres size, Redis memory, RabbitMQ messages.

### 3. Phân hệ Đăng nhập/Đăng ký (`features/auth`)
* **LoginPage** và **RegisterPage** chỉ xử lý hiển thị form và gán sự kiện.
* Toàn bộ việc kiểm tra regex định dạng email, so khớp mật khẩu xác nhận, quản lý trạng thái nút bấm `isSubmitting` và thông báo lỗi được đóng gói an toàn trong `hooks/useLogin.ts` và `hooks/useRegister.ts`.
* `api/authApi.ts` đóng gói các request đăng nhập, đăng ký và lấy hồ sơ hiện tại; `dtos/authDto.ts` build payload và parse response/error; `types/auth.ts` giữ contract TypeScript; `states/AuthContext.tsx` là state trung tâm cho phiên đăng nhập, token JWT và thông tin vai trò người dùng.

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
* **Metrics hệ thống**: Admin metrics dashboard sử dụng API `/api/admin/metrics` của Backend. Backend hoạt động như một lớp trung gian truy vấn Prometheus và tổng hợp kết quả (sử dụng Redis cache 10 giây), bảo vệ an toàn các chỉ số vận hành sau lớp xác thực tài khoản Admin. Frontend không scrape trực tiếp; traffic frontend được quan sát qua Nginx target.
