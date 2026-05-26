# Tài liệu giải thích Backend

## Mục đích

Thư mục `backend/` chứa dịch vụ FastAPI giao tiếp trực tiếp với giao diện người dùng thông qua cổng ngược Nginx (UI-facing API). Dịch vụ này đảm nhận các nhiệm vụ: quản lý các API công khai, xác thực yêu cầu (validation), lưu trữ thông tin trạng thái (metadata), tải tệp tin lên bộ lưu trữ đối tượng MinIO, xuất bản (publish) công việc vào hàng đợi RabbitMQ, truy vấn trạng thái/kết quả từ Redis hoặc PostgreSQL, và trả về dữ liệu thống kê tổng hợp cho Dashboard.

Backend hoàn toàn **không** chạy trực tiếp bất kỳ mô hình ASR hay LLM nào, nhằm giữ cho API luôn cực kỳ nhẹ nhàng và phản hồi thời gian thực. Tất cả các tác vụ xử lý nặng được chuyển giao không đồng bộ cho bộ đôi microservices `voice-worker` và `llm-worker`.

---

## Cấu trúc thư mục

```text
backend/
├── app/main.py                         ← Điểm khởi chạy FastAPI và áp dụng tự động migrations DB
├── app/core/config.py                  ← Cấu hình môi trường cho Backend (kết nối DB, Cache, Queue, MinIO)
├── app/domain/analysis.py              ← Định nghĩa các kiểu dữ liệu Domain của Job/Result
├── app/application/use_cases/          ← Use cases gửi công việc phân tích âm thanh/văn bản
├── app/infrastructure/database/        ← Khởi tạo SQLAlchemy models/session/repository
│   ├── models.py                       ← ORM models: AnalysisJobModel, AnalysisResultModel
│   ├── analysis_repository.py          ← Repository: CRUD + get_analytics_stats()
│   └── session.py                      ← SQLAlchemy session factory
├── app/infrastructure/storage/         ← Bộ điều hợp tải tệp tin âm thanh lên MinIO bucket
├── app/infrastructure/cache/           ← Bộ điều hợp đọc nhanh trạng thái công việc từ Redis
├── app/infrastructure/queue/           ← Bộ điều hợp xuất bản công việc vào hàng đợi RabbitMQ
├── app/interfaces/controllers/         ← Các bộ điều khiển HTTP (Health và Analysis controllers)
│   └── analysis_controller.py          ← Toàn bộ các route phân tích + stats
├── app/interfaces/schemas/             ← Pydantic schemas cho request/response validation
│   └── analysis_schema.py              ← JobAcceptedResponse, JobStatusResponse, SessionListResponse...
└── alembic/versions/                   ← Các file migration Alembic tự động
    ├── 0001_initial.py
    ├── 0002_add_session_name.py
    └── 0003_add_agent_evaluation.py    ← Bổ sung agent_score & agent_advice_json
```

---

## Cấu Trúc Cơ Sở Dữ Liệu (Database Schema)

### Bảng `analysis_jobs`

| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | UUID | Khoá chính định danh duy nhất mỗi Job |
| `name` | VARCHAR(256) | Tên hiển thị tùy chỉnh (có thể đổi tên bằng `PATCH`) |
| `input_type` | VARCHAR(16) | Loại đầu vào: `audio` hoặc `text` |
| `status` | VARCHAR(16) | Trạng thái: `pending` → `processing` → `completed` / `failed` |
| `audio_object_key` | VARCHAR(512) | Đường dẫn file âm thanh trong MinIO bucket `uploads` |
| `submitted_text` | TEXT | Nội dung văn bản gốc khi `input_type = text` (dành cho audit trail) |
| `error_message` | TEXT | Mô tả lỗi nếu Job thất bại |
| `created_at` | TIMESTAMPTZ | Thời điểm tạo Job |
| `updated_at` | TIMESTAMPTZ | Thời điểm cập nhật trạng thái gần nhất |

### Bảng `analysis_results`

| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | UUID | Khoá chính |
| `job_id` | UUID FK | Liên kết 1-1 tới `analysis_jobs.id` |
| `transcript_json` | JSONB | Danh sách lượt hội thoại `[{speaker, text, start_seconds, end_seconds}]` |
| `summary_json` | JSONB | Danh sách bullet points tóm tắt cuộc gọi |
| `sentiment` | VARCHAR(32) | Sắc thái cảm xúc tổng thể: `positive` / `neutral` / `negative` |
| `sentiment_reason` | TEXT | Lý do đánh giá sắc thái từ LLM |
| `confidence` | FLOAT | Điểm tự tin 0.0–1.0 của LLM |
| `agent_score` | INT (nullable) | Điểm đánh giá nhân viên 0–10 từ LLM |
| `agent_advice_json` | JSONB (nullable) | Danh sách lời khuyên hành động từ LLM cho nhân viên |
| `created_at` | TIMESTAMPTZ | Thời điểm tạo kết quả |

---

## Luồng chạy hệ thống (Runtime Flow)

1.  **Phân tích âm thanh**: Khi giao diện gọi `POST /api/analysis/audio`, Backend sẽ lưu tệp tin âm thanh nhận được vào bộ lưu trữ đối tượng MinIO bucket `uploads`, tạo một bản ghi trạng thái trong bảng `analysis_jobs` của PostgreSQL với trạng thái ban đầu là `pending`, xuất bản một tin nhắn chứa ID công việc vào hàng đợi `analysis.jobs` của RabbitMQ, sau đó trả về ngay lập tức mã `job_id` cùng trạng thái `pending`.
2.  **Phân tích văn bản**: Khi giao diện gọi `POST /api/analysis/text`, Backend tạo trực tiếp bản ghi công việc dạng văn bản trong PostgreSQL (lưu `submitted_text` gốc cho audit) và đẩy tin nhắn phân tích kèm nội dung văn bản vào hàng đợi `analysis.jobs` của RabbitMQ.
3.  **Tra cứu kết quả**: Khi giao diện gọi `GET /api/analysis/{job_id}`, Backend sẽ truy vấn bộ nhớ đệm **Redis** trước để phản hồi siêu tốc dưới 1ms. Nếu không tìm thấy trong Redis, nó sẽ thực hiện truy vấn cơ sở dữ liệu **PostgreSQL**. Khi công việc hoàn thành (`completed`), kết quả trả về sẽ bao gồm: đoạn hội thoại (transcript), danh sách tóm tắt (summary), sắc thái cảm xúc (sentiment), lý do đánh giá, điểm tự tin (confidence), **điểm nhân viên (agent_score)**, và **lời khuyên nhân viên (agent_advice)**.
4.  **Danh sách phiên**: `GET /api/analysis` trả về danh sách các phiên phân tích có phân trang (`limit`, `offset`), kèm tổng số và sentiment tóm tắt mỗi phiên.
5.  **Thống kê Dashboard**: `GET /api/analysis/stats` tổng hợp: tổng số phân tích, phân phối sentiment (tích cực/trung lập/tiêu cực), điểm nhân viên trung bình, và xu hướng 7 ngày gần nhất.

---

## Các Cổng Dịch Vụ Công Khai (Endpoints)

Dịch vụ backend chạy trên cổng nội bộ `8000` của container và được định tuyến thông qua cổng Nginx ngược (`9090` trên host) tại các địa chỉ:

| Phương thức | Đường dẫn | Mục đích |
|---|---|---|
| GET | `/health` | Kiểm tra tình trạng hoạt động (health check) của Backend |
| POST | `/api/analysis/audio` | Tải lên file âm thanh (`.mp3`, `.wav`, `.webm`, `.mp4`) |
| POST | `/api/analysis/text` | Gửi trực tiếp văn bản hội thoại để phân tích nhanh |
| GET | `/api/analysis` | Danh sách phiên phân tích (hỗ trợ `limit`, `offset`) |
| GET | `/api/analysis/stats` | **[MỚI]** Số liệu thống kê tổng hợp cho Dashboard |
| GET | `/api/analysis/{job_id}` | Lấy trạng thái và kết quả chi tiết của một phiên |
| PATCH | `/api/analysis/{job_id}` | **[MỚI]** Đổi tên phiên phân tích |
| DELETE | `/api/analysis/{job_id}` | **[MỚI]** Xoá phiên + file MinIO + cache Redis |

---

## Quản lý Di cư Cơ sở Dữ liệu (Database Migrations - Alembic)

Dịch vụ backend quản lý trực tiếp cấu trúc bảng cơ sở dữ liệu PostgreSQL bằng công cụ **Alembic**. Khi container backend được khởi chạy, một tập lệnh tự động di cư (`command.upgrade(cfg, "head")`) sẽ chạy trước khi khởi tạo uvicorn server nhằm đảm bảo các bảng dữ liệu cần thiết được tạo lập và đồng bộ tự động lên phiên bản mới nhất (`head`).

Các script di cư được đặt tại `backend/alembic/versions/`:
- `0001_initial.py` — Tạo bảng `analysis_jobs` và `analysis_results` cơ bản.
- `0002_add_session_name.py` — Thêm cột `name` cho bảng `analysis_jobs`.
- `0003_add_agent_evaluation.py` — Thêm cột `agent_score` và `agent_advice_json` cho bảng `analysis_results`.

---

## Bảo Mật Đường Truyền & Mạng Nội Bộ (Security & Isolation)

> [!IMPORTANT]
> **Container Isolation**: Cổng container `8000` của Backend hoàn toàn **không được ánh xạ ra ngoài host**. Mọi giao tiếp từ người dùng bên ngoài hay Frontend trình duyệt đều bắt buộc phải đi qua Reverse Proxy Nginx ở cổng **`9090`**. Thiết lập này giúp bảo vệ tối đa các Endpoint nghiệp vụ, ngăn chặn tấn công bypass trực diện và tuân thủ chặt chẽ nguyên tắc bảo mật production-grade.
