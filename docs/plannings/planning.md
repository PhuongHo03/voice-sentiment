# Lộ trình phát triển dự án Voice Sentiment

| Hạng mục | Trạng thái hiện tại |
|---|---|
| **Giai đoạn hiện tại** | ✅ Giai đoạn 4 — Dashboard Thống Kê & Đánh Giá Hiệu Suất Nhân Viên |
| **Giai đoạn tiếp theo** | ⏳ Giai đoạn 5 — Viết unit/integration tests tập trung và tối ưu hóa hiệu năng |
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
  - [x] **Chẩn đoán Lỗi STT Timeout**: Xác định và hướng dẫn xử lý lỗi `Voice-worker STT service connection failed: timed out` khi voice-worker chưa sẵn sàng hoặc quá tải.

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

### Giai đoạn 5 — Viết Unit/Integration Tests & Ổn Định Hệ Thống (Kế hoạch tiếp theo)
*   **Unit Tests**: Viết kiểm thử thành phần cho các Repositories, Use Cases, và AI Clients của cả `backend`, `voice-worker`, và `llm-worker`.
*   **Integration Tests**: Giả lập các luồng gửi tin nhắn RabbitMQ bị ngắt quãng, mất kết nối cơ sở dữ liệu PostgreSQL/Redis để củng cố độ bền bỉ (resilience) của Worker.
*   **Load Testing**: Đo lường thời gian xử lý khi gửi liên tục nhiều yêu cầu chuyển giọng nói cùng lúc lên `voice-worker` để đánh giá khả năng chịu tải trên CPU máy chủ.
