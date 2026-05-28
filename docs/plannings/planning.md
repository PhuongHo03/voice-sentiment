# Lộ trình phát triển dự án Voice Sentiment

| Hạng mục | Trạng thái hiện tại |
|---|---|
| **Giai đoạn hiện tại** | 🔄 Giai đoạn 8 — Tối ưu hóa Toàn diện & Triển khai Production |
| **Giai đoạn tiếp theo** | ⏳ Giai đoạn 9 — Bảo trì & Mở rộng Tính năng |
| **Thư mục gốc workspace** | `D:\voice-sentiment` |

---

## Cấu Trúc Dự Án Hiện Tại (Decoupled Microservices)

```text
├── voice-worker/         ← Dịch vụ ASR giải mã âm thanh stateless (FastAPI + local CPU Whisper)
├── llm-worker/           ← Dịch vụ điều phối xử lý nền (RabbitMQ consumer + LLM client)
├── backend/              ← FastAPI Gateway công khai, quản lý trạng thái metadata và migrations DB
├── frontend/             ← Giao diện Admin Dashboard React/Vite/TypeScript trực quan
├── docs/                 ← Thư mục tài liệu hướng dẫn và phân tích kiến trúc dự án
│   ├── explanations/     ← Tài liệu chi tiết của từng thành phần (backend, frontend, worker, infra)
│   └── plannings/        ← Tài liệu lộ trình và quy hoạch phát triển hệ thống
├── docker-compose.yml    ← Khai báo toàn bộ hạ tầng microservices (Postgres, Redis, RabbitMQ, MinIO, Nginx...)
└── nginx.conf            ← File cấu hình Reverse Proxy Nginx cục bộ trỏ cổng host 9090
```

---

## Các Công Nghệ Vận Hành (Runtime Stack)

*   **PostgreSQL (`5432`)**: Lưu trữ bền vững dữ liệu nghiệp vụ cuộc gọi, bản ghi hội thoại và kết quả phân tích (bao gồm `agent_score`, `agent_advice_json`).
*   **MinIO (`9000`, Console `9092`)**: Lưu trữ tệp tin đối tượng cho các file âm thanh ghi âm gốc.
*   **Redis (`6379`, Insight `9093`)**: Lưu trữ bộ nhớ đệm cache trạng thái công việc để phản hồi UI siêu tốc.
*   **RabbitMQ (`5672`, Console `9094`)**: Bộ trung chuyển hàng đợi tin nhắn không đồng bộ `analysis.jobs`.
*   **Nginx Proxy (`9090`)**: Cổng ngõ vào (Gateway) duy nhất của hệ thống phục vụ Web UI và định tuyến các API backend.
*   **Adminer (`9091`)**: Công cụ Web UI gọn nhẹ quản trị cơ sở dữ liệu PostgreSQL.
*   **local Whisper (Cổng `9095` nội bộ `8000`)**: Máy chủ `voice-worker` chạy `faster-whisper` giải mã ASR trực tiếp trên CPU bằng lượng tử hóa `int8` cực kỳ tối ưu RAM.
*   **Remote LLM (External)**: Đầu cuối mô hình LLM tương thích OpenAI chạy tại địa chỉ IP máy chủ của bạn (`192.168.2.74:8007`) đảm nhận phân tích sắc thái và đánh giá nhân viên.

---

## Danh Sách Công Việc Đã Hoàn Thành (Achievements)

- [x] **Giai đoạn 1**: Xây dựng cấu trúc Clean Architecture cơ bản và kết nối bộ khung Docker Compose thô.
- [x] **Giai đoạn 2**: Tích hợp mô hình cục bộ `faster-whisper` trên CPU, đấu nối LLM thực tế, loại bỏ hoàn toàn 100% Mock Fallback và cấu hình migrations DB tự động bằng Alembic.
- [x] **Giai đoạn 2.5/3**:
  - [x] Phân tách thành công nền tảng xử lý từ một background worker cồng kềnh thành bộ đôi độc lập: `voice-worker` (Stateless ASR) và `llm-worker` (Stateful Orchestrator).
  - [x] Quy hoạch và đồng bộ dải cổng dịch vụ trên host liên tục từ **`9090` đến `9095`** giúp hệ thống cực kỳ khoa học và chuyên nghiệp.
  - [x] Ẩn hoàn toàn các cổng container máy chủ ứng dụng `backend` (`8000`) và `frontend` (`5173`) để thiết lập bức tường lửa bảo mật thông qua Gateway Nginx (`9090`).
  - [x] Tích hợp tự động nhận diện ngôn ngữ STT (`auto`) tăng tính linh hoạt khi giải mã hội thoại âm thanh.
  - [x] Chạy kiểm thử tự động E2E thành công 100% trên cả 2 đường ống phân tích âm thanh và văn bản thực tế.
- [x] **Giai đoạn 4**:
  - [x] **Quản lý Phiên (Session Management)**: Thêm sidebar lịch sử phiên phân tích có thể tìm kiếm, đổi tên (inline rename), xoá từng phiên, và lọc theo từ khoá thông qua các API `GET /api/analysis`, `PATCH /api/analysis/{id}`, `DELETE /api/analysis/{id}`.
  - [x] **Đánh Giá Nhân Viên (Agent Evaluation)**: LLM tự động tính điểm nhân viên (`agent_score` 0–10) và sinh lời khuyên hành động (`agent_advice`) sau mỗi cuộc gọi. Kết quả lưu vào cột `agent_score` và `agent_advice_json` của bảng `analysis_results` qua migration Alembic `0003_add_agent_evaluation.py`.
  - [x] **Dashboard Thống Kê**: Thêm nút "Phân tích cuộc gọi" trên sidebar để chuyển sang chế độ xem Dashboard hiển thị biểu đồ vòng sắc thái (SVG donut), phân phối điểm nhân viên (bar chart), và xu hướng phân tích theo tuần.
  - [x] **API Thống Kê**: Thêm endpoint `GET /api/analysis/stats` trả về dữ liệu tổng hợp gồm số lượng phân tích, phân phối sentiment, điểm nhân viên trung bình, và xu hướng 7 ngày gần nhất.
  - [x] **UX Cải Tiến**: Đổi biểu tượng "Phân tích cuộc gọi" thành icon SVG phù hợp hơn; sửa lỗi CSS khung bao quanh nhỏ khi chọn item trong sidebar.
  - [x] **Chẩn đoán Lỗi STT Timeout**: Xác định và hướng dẫn xử lý lỗi `Voice-worker STT service connection failed: timed out` when voice-worker chưa sẵn sàng hoặc quá tải.
- [x] **Giai đoạn 7**:
  - [x] **Unit Tests**: Xây dựng bộ unit tests bằng `pytest` phủ kín các logic lõi cho `backend` (đạt 91%-100% các file Use Cases & AuthService), `voice-worker`, và `llm-worker` sử dụng mock cô lập.
  - [x] **Resilience Integration**: Viết script `verify_resilience.py` giả lập sập hạ tầng Postgres, Redis, RabbitMQ. Chứng minh hệ thống tự khôi phục kết nối và không bị crash đơ máy chủ.
  - [x] **Load Testing**: Thiết lập script kiểm thử bất đồng bộ song song `load_test_whisper.py` gửi đồng thời nhiều request để chứng thực năng lực phản hồi (8 rps, latency trung bình 0.06s).
  - [x] **Tối ưu hóa Frontend (Custom Hooks Separation)**: Tách triệt để toàn bộ logic nghiệp vụ (API, state, effects) ra khỏi các tệp Pages (`DashboardPage`, `AdminDashboardPage`, `LoginPage`, `RegisterPage`) vào các Custom Hooks độc lập có kiểu dữ liệu mạnh mẽ, giúp tối giản từ 30% - 45% mã nguồn Pages, biên dịch thành công 100% không lỗi.
  - [x] **Cấu hình biến môi trường tập trung (Master `.env` ở Root)**: Hợp nhất toàn bộ các tệp `.env` phân mảnh của các services thành 1 tệp `.env` duy nhất ở ngoài root của dự án. Đồng bộ hóa với `docker-compose.yml` theo chuẩn thiết kế 12-Factor App để sẵn sàng cho đóng gói Production và đăng tải Docker Hub.
  - [x] **Hệ thống Caching & Invalidation nâng cao (Advanced Caching)**: Thiết lập bộ nhớ đệm cho Dashboard Stats (TTL 24h), tự động xóa cache thông minh khi kết thúc Job (ở `llm-worker`) hoặc khi xóa phiên (ở `backend`). Đồng thời ghi đè cache `pending` khi tạo Job giúp giảm tải PostgreSQL Polling về mức tuyệt đối **0%**.

---

## Lộ Trình Chi Tiết Các Giai Đoạn

### Giai đoạn 1 — MVP Scaffold (Hoàn thành)
Thiết lập bộ khung Clean Architecture thô, cấu hình Docker Compose ban đầu, tạo giao diện thô cho phép ghi âm và hiển thị kết quả.

### Giai đoạn 2 — Tích Hợp ASR/LLM Thực Tế & Loại Bỏ Mock (Hoàn thành)
Thay thế Riva bằng `faster-whisper` trên CPU cục bộ, chuẩn hóa âm thanh đầu vào WebM từ microphone bằng FFmpeg pipe, đấu nối OpenAI-compatible API bên ngoài, đồng bộ hóa database PostgreSQL tự động qua Alembic khi khởi tạo container, loại bỏ hoàn toàn dữ liệu giả lập.

### Giai đoạn 3 — Phân Tách Worker & Quy Hoạch Dải Cổng 9090-9095 (Hoàn thành)
*   Tách dịch vụ AI thành `voice-worker` (stateless API phục vụ chung cho cả mạng nội bộ) và `llm-worker` (orchestration xử lý nền không phơi cổng).
*   Ánh xạ toàn bộ cổng host sang dải liên tục bảo mật `9090-9095`.
*   Kiểm chứng toàn bộ luồng hoạt động thông qua kịch bản `verify.py` đạt hiệu năng xử lý cực cao nhờ cơ chế in-memory caching mô hình Whisper của `voice-worker`.

### Giai đoạn 4 — Dashboard Thống Kê & Đánh Giá Nhân Viên (Hoàn thành)
*   **Cơ sở dữ liệu**: Thêm migration `0003_add_agent_evaluation.py` bổ sung cột `agent_score` (INT) và `agent_advice_json` (JSONB) vào `analysis_results`.
*   **Backend API mới**: Endpoint `GET /api/analysis/stats` tổng hợp phân phối sentiment, điểm nhân viên, và xu hướng 7 ngày; `GET /api/analysis` danh sách phiên; `PATCH` đổi tên; `DELETE` xoá phiên.
*   **LLM Worker**: Cập nhật prompt yêu cầu LLM trả về thêm `agent_score` và `agent_advice` trong JSON; lưu vào DB sau phân tích.
*   **Frontend Dashboard**: Thêm panel sidebar lịch sử phiên (search, rename, delete); thêm tab Dashboard thống kê với biểu đồ SVG donut, bar chart, và weekly trends; thêm thẻ Scorecard nhân viên hiển thị điểm vòng tròn động và lời khuyên từ AI.

### Giai đoạn 5 — Xác Thực, Phân Quyền (RBAC) & Dashboard Quản Trị Admin (Hoàn thành)
*   **Cơ sở dữ liệu (Database Schema)**:
    *   Thiết kế bảng riêng `roles` (`id`, `name`, `description`) để quản lý nghiêm ngặt vai trò tài khoản (các vai trò mặc định: `admin`, `employee`).
    *   Thiết kế bảng `users` (`id`, `username`, `email`, `hashed_password`, `role_id`, `created_at`, `is_active`) liên kết khoá ngoại với bảng `roles`.
    *   Bổ sung khoá ngoại `owner_id` vào bảng `analysis_jobs` (liên kết với bảng `users`) thông qua migrations Alembic. Mỗi tài khoản người dùng (bao gồm cả tài khoản nhân viên thường và tài khoản admin) đều sở hữu tập hợp các phiên (`sessions`) phân tích và biểu đồ dashboard cá nhân hoàn toàn độc lập.
*   **Backend Auth & Phân quyền API**:
    *   Đăng ký & Đăng nhập: Cung cấp các endpoint công khai `POST /api/auth/register` và `POST /api/auth/login` cấp mã JWT Token bảo mật. Tự động liên kết vai trò mặc định khi đăng ký.
    *   Phòng vệ API: Xây dựng FastAPI dependency `get_current_user` phục vụ việc giải mã Token, trích xuất thông tin người dùng và xác thực quyền hạn.
    *   Cách ly dữ liệu cá nhân: Mọi tài khoản (cả nhân viên lẫn admin) khi gọi API phân tích `GET /api/analysis`, `POST /api/analysis` hoặc truy vấn stats cá nhân `GET /api/analysis/stats` đều chỉ thao tác trên các phiên do chính mình sở hữu (`owner_id = current_user.id`).
    *   API Admin quản lý tiến độ: Endpoint `GET /api/admin/employees` trả về thông tin danh sách nhân viên kèm thống kê tiến độ làm việc, điểm số trung bình, và hiệu năng tổng quát.
*   **Giao diện Đăng nhập & Đăng ký (Frontend Auth)**:
    *   Trang Login/Register chuyên nghiệp sử dụng CSS thuần tuý, đồng bộ với thiết kế giao diện tối (dark mode) sang trọng hiện tại.
    *   Tích hợp Auth Context/State quản lý trạng thái đăng nhập, tự động đính kèm Token vào HTTP Header cho mọi cuộc gọi API.
    *   Định tuyến bảo vệ (Protected Routes): Điều hướng người dùng chưa đăng nhập về trang Login; ngăn chặn Nhân viên truy cập trái phép vào các trang quản trị của Admin.
*   **Giao diện Dashboard Admin Quản lý Tiến độ**:
    *   Phân tách rõ ràng: Tài khoản Admin sẽ có đầy đủ **Dashboard cá nhân riêng** (hiển thị thống kê các cuộc gọi/phân tích do chính admin thực hiện) giống như một nhân viên, và **Dashboard quản trị tiến độ nhân viên riêng**.
    *   Bảng theo dõi tổng quan tiến độ (Overview Grid): Dành riêng cho vai trò `admin`, liệt kê danh sách tất cả các tài khoản nhân viên kèm số lượng phiên đã xử lý, điểm đánh giá trung bình `agent_score`, và sắc thái chủ đạo.
    *   Bộ lọc & Xem chi tiết: Cho phép Admin chọn xem chi tiết tiến độ một nhân viên bất kỳ để hiển thị biểu đồ tròn sắc thái, phân phối điểm và xu hướng tuần của riêng nhân viên đó.

### Giai đoạn 6 — Phân Tách Cô Lập Hạ Tầng (Tenant-Isolated Infra) & Tối Ưu Hóa Hiệu Năng (Hoàn thành)
*   **MinIO (Phân tách Prefix cô lập)**: 
    *   Cấu hình cơ chế lưu trữ file âm thanh ghi âm gốc phân tách theo prefix chứa ID người dùng (`owner_id`) dưới dạng `uploads/{owner_id}/{filename}` thay vì lưu chung một thư mục.
    *   Đảm bảo tính cô lập dữ liệu tuyệt đối giữa các tài khoản ở tầng lưu trữ đối tượng vật lý (Object Storage).
*   **Redis (Đặt tiền tố Cache theo User)**:
    *   Thiết lập cơ chế sinh Key Cache của Redis có đính kèm Namespace theo mã tài khoản (`cache:user:{owner_id}:analysis:{job_id}`).
    *   Tránh xung đột cache khi nhiều nhân viên thực hiện thao tác đồng thời và tăng tốc truy vấn Dashboard lịch sử riêng biệt.
*   **RabbitMQ (Mở rộng Multi-Queue & Cấu hình Động)**:
    *   Nâng cấp cơ chế phân phối job từ 1 queue duy nhất lên thành mô hình **Đa hàng đợi (Multi-Queue)**, bắt đầu chạy thử nghiệm với 2 queue để đánh giá hiệu năng chịu tải và giới hạn xử lý song song của các Worker.
    *   Đưa số lượng Queue cần khởi tạo vào biến môi trường `.env` (`RABBITMQ_QUEUE_COUNT=2`) để dễ dàng tuỳ chỉnh, tăng giảm quy mô (scaling) khi đưa lên Production mà không cần thay đổi source code.

### Giai đoạn 7 — Viết Unit/Integration Tests & Ổn Định Hệ Thống (Hoàn thành)
*   **Unit Tests**: Viết kiểm thử thành phần cho các Repositories, Use Cases, và AI Clients của cả `backend`, `voice-worker`, và `llm-worker` đạt độ phủ cao.
*   **Integration Tests**: Giả lập các luồng gửi tin nhắn RabbitMQ bị ngắt quãng, mất kết nối cơ sở dữ liệu PostgreSQL/Redis để củng cố độ bền bỉ (resilience) của các dịch vụ thông qua script tự động `verify_resilience.py`.
*   **Load Testing**: Đo lường và đánh giá năng lực chịu tải mạng đồng thời của `voice-worker` thông qua script bất đồng bộ song song `load_test_whisper.py` đạt tỷ lệ thành công 100%.
*   **Tái cấu trúc Frontend (Tách Custom Hooks)**: Phân tách hoàn chỉnh mã nguồn hiển thị khỏi logic nghiệp vụ của các trang `DashboardPage`, `AdminDashboardPage`, `LoginPage` và `RegisterPage` thành các hooks chuyên biệt có kiểu dữ liệu mạnh (`useDashboardAnalysis`, `useAdminDashboard`, `useLogin`, `useRegister`), giúp frontend đạt cấu trúc mô hình hóa chuẩn tắc của React, dễ dàng nâng cấp giao diện mà không ảnh hưởng logic bên dưới.
*   **Hệ thống cấu hình tập trung (Master `.env`)**: Thiết lập và tích hợp tệp `.env` duy nhất ở ngoài root của dự án để quản lý tập trung toàn bộ biến môi trường của các dịch vụ microservices (`backend`, `frontend`, `voice-worker`, `llm-worker`), đồng bộ hóa cùng `docker-compose.yml` theo chuẩn **12-Factor App**. Đảm bảo các Docker Images hoàn toàn không chứa bất kỳ mã nhạy cảm nào (Immutable Images), tăng tốc quy mô triển khai Production và đưa lên Docker Hub.
*   **Tối ưu hóa Caching & Invalidation (Advanced Caching)**:
    *   **Dashboard Stats Caching**: Nhất quán lưu cache dữ liệu thống kê biểu đồ tròn và cột của Dashboard trong Redis với thời gian sống 24h, tự động thu hồi (evict) thông minh khi `llm-worker` hoàn thành phân tích một job hoặc khi backend xóa một phiên, giúp tránh các câu lệnh SQL `COUNT/AVG` đắt đỏ trong cơ sở dữ liệu PostgreSQL.
    *   **Pending Job Caching**: Ghi đè trạng thái `pending` của Job ngay khi vừa khởi tạo ở Backend giúp tránh hoàn toàn gánh nặng truy vấn database của cuộc gọi Polling đầu tiên từ phía giao diện, đưa tải PostgreSQL Polling về mức tuyệt đối 0%.

### Giai đoạn 8 — Tối ưu hóa Toàn diện & Triển khai Production (Đang thực hiện)
*   **CI/CD**: Tích hợp các bộ kiểm thử tự động của Giai đoạn 7 vào luồng GitHub Actions CI/CD để tự động chạy kiểm thử trước mỗi lần đóng gói (bao gồm unit tests của backend, voice-worker, llm-worker và build verification của frontend).
