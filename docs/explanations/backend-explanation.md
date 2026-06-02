# Tài liệu giải thích Backend

## Mục đích

Thư mục `backend/` chứa dịch vụ FastAPI giao tiếp trực tiếp với giao diện người dùng thông qua cổng ngược Nginx (UI-facing API Gateway). Dịch vụ này đảm nhận các nhiệm vụ:
- Xác thực và phân quyền người dùng thông qua chuẩn bảo mật mã hóa JWT (JSON Web Tokens).
- Phân biệt vai trò người dùng (Role-Based Access Control - RBAC) như `admin` (Quản trị viên) và `employee` (Nhân viên).
- Cung cấp các API công khai phục vụ việc tải file ghi âm lên bộ lưu trữ đối tượng MinIO cô lập theo thư mục từng người dùng (`owner_id`).
- Xuất bản (publish) không đồng bộ các công việc phân tích âm thanh/văn bản vào hàng đợi RabbitMQ.
- Đọc nhanh trạng thái công việc đang xử lý từ Redis cache và lưu trữ kết quả cuối cùng bền vững vào PostgreSQL.
- Tổng hợp thống kê hiệu suất cá nhân và tổng quan toàn hệ thống phục vụ hiển thị Dashboard.

Dịch vụ backend hoàn toàn **stateless** và không chạy trực tiếp bất kỳ mô hình AI nặng nề nào. Mọi tác vụ tính toán ASR (Speech-to-Text) và LLM phân tích cảm xúc đều được đẩy về cho các worker độc lập (`voice-worker` và `llm-worker`).

---

## Cấu trúc thư mục

```text
backend/
├── app/main.py                         ← Khởi chạy FastAPI, đăng ký routers và tự động đồng bộ DB schema qua Alembic
├── app/configs/                        ← Cấu hình môi trường, SQLAlchemy session, Redis, RabbitMQ, MinIO
│   ├── config.py                       ← Pydantic Settings (DB, Cache, Queue, MinIO, JWT, CORS)
│   ├── session.py                      ← Factory kết nối cơ sở dữ liệu
│   ├── cache.py                        ← Redis adapter với namespace theo người dùng
│   ├── queue.py                        ← Đẩy tin nhắn không đồng bộ vào đa hàng đợi RabbitMQ
│   ├── metrics.py                      ← Prometheus /metrics, HTTP latency/counter và business counters
│   └── storage.py                      ← Tải file âm thanh lên MinIO cô lập theo uploads/{owner_id}/...
├── app/controllers/                    ← HTTP routing mỏng: Auth, Analysis, Files, Admin, Health
├── app/dtos/                           ← Pydantic schemas xác thực request/response payload
├── app/services/                       ← Luồng nghiệp vụ: auth, analysis, file storage, admin operations
├── app/repositories/                   ← SQLAlchemy data access cho users, admin queries, analysis jobs/results
├── app/models/models.py                ← ORM models: Role, User, AnalysisJobModel, AnalysisResultModel
├── app/middlewares/dependencies.py     ← FastAPI dependencies xác thực JWT và kiểm tra quyền admin
└── alembic/versions/                   ← Tập lệnh migration tự động khởi tạo cơ sở dữ liệu
    └── 0001_initial_schema.py          ← Tập lệnh hợp nhất khởi tạo đầy đủ Schema & Dữ liệu Seed ban đầu
```

---

## Cấu Trúc Cơ Sở Dữ Liệu (Database Schema)

Hệ thống cơ sở dữ liệu được tổ chức chặt chẽ để đảm bảo tính toàn vẹn dữ liệu và phân tách tài khoản người dùng:

### 1. Bảng `roles` (Vai trò)
| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | VARCHAR(32) PK | Định danh vai trò (`admin`, `employee`) |
| `name` | VARCHAR(64) | Tên vai trò |
| `description` | VARCHAR(256) | Mô tả chi tiết quyền hạn vai trò |

### 2. Bảng `users` (Tài khoản)
| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID định danh tài khoản người dùng |
| `username` | VARCHAR(128) | Tên tài khoản đăng nhập (Unique) |
| `email` | VARCHAR(128) | Địa chỉ Email liên hệ (Unique) |
| `hashed_password`| VARCHAR(256) | Mật khẩu mã hóa bảo mật Bcrypt |
| `is_active` | BOOLEAN | Trạng thái tài khoản (Chờ duyệt `false`, Kích hoạt `true`) |
| `created_at` | TIMESTAMPTZ | Ngày giờ đăng ký tài khoản |

### 3. Bảng `user_role` (Liên kết vai trò)
Bảng trung gian liên kết 1-nhiều hoặc nhiều-nhiều giữa bảng `users` và `roles` (để hỗ trợ gán nhiều vai trò trong tương lai).
* `user_id`: Khóa ngoại liên kết bảng `users` (`ondelete='CASCADE'`).
* `role_id`: Khóa ngoại liên kết bảng `roles` (`ondelete='CASCADE'`).

### 4. Bảng `analysis_jobs` (Phiên làm việc)
| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID định danh phiên phân tích |
| `name` | VARCHAR(256) | Tiêu đề tùy chỉnh của phiên (có thể đổi tên) |
| `input_type` | VARCHAR(16) | Loại đầu vào: `audio` hoặc `text` |
| `status` | VARCHAR(16) | Trạng thái: `pending` → `processing` → `completed` / `failed` |
| `audio_object_key`| VARCHAR(512) | Đường dẫn vật lý file ghi âm trong MinIO: `uploads/{owner_id}/{filename}` |
| `submitted_text` | TEXT | Văn bản thô đầu vào |
| `error_message` | TEXT | Nội dung chi tiết lỗi nếu Job thất bại |
| `owner_id` | VARCHAR(36) FK | Khóa ngoại liên kết với `users.id` để phân tách dữ liệu cá nhân |
| `created_at` | TIMESTAMPTZ | Thời điểm khởi tạo phiên |
| `updated_at` | TIMESTAMPTZ | Thời điểm cập nhật trạng thái gần nhất |

### 5. Bảng `analysis_results` (Kết quả phân tích)
| Cột | Kiểu | Mô tả |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID định danh kết quả |
| `job_id` | VARCHAR(36) FK | Khóa ngoại liên kết 1-1 tới `analysis_jobs.id` |
| `transcript_json`| JSONB | Nội dung cuộc gọi đã phân đoạn: `[{speaker, text, start_seconds, end_seconds}]` |
| `summary_json` | JSONB | Tóm tắt các ý chính dạng danh sách |
| `sentiment` | VARCHAR(32) | Sắc thái tổng thể cuộc gọi: `positive` / `neutral` / `negative` |
| `sentiment_reason`| TEXT | Lý do phân tích sắc thái cảm xúc từ LLM |
| `confidence` | FLOAT | Chỉ số độ tự tin 0.0 - 1.0 của LLM |
| `agent_score` | INT | Điểm kỹ năng chăm sóc khách hàng của nhân viên (0-100đ) |
| `agent_advice_json`| JSONB | Lời khuyên hành động thông minh từ AI cho nhân viên |
| `created_at` | TIMESTAMPTZ | Ngày giờ lưu kết quả |

---

## Luồng xử lý nghiệp vụ (Runtime Flow)

1. **Xác thực yêu cầu**: Mọi yêu cầu tới API nghiệp vụ (trừ Đăng nhập/Đăng ký) đều phải gửi kèm JWT token qua Header `Authorization: Bearer <token>`. Dependency `get_current_user` trong `app/middlewares/dependencies.py` sẽ xác minh tính hợp lệ và truy xuất thông tin tài khoản đang thao tác qua `UserRepository`.
2. **Gửi yêu cầu phân tích**:
   - **Âm thanh**: File âm thanh tải lên được đẩy vào MinIO với đường dẫn cô lập chứa ID người dùng (`uploads/{owner_id}/{filename}`). Backend ghi nhận một Job mới trạng thái `pending` trong Postgres (gán `owner_id = current_user.id`), đẩy tin nhắn công việc vào hàng đợi RabbitMQ (`analysis.jobs`), và trả về `job_id` lập tức.
   - **Văn bản**: Backend ghi nhận Job mới trong Postgres, đẩy tin nhắn thô chứa văn bản trực tiếp vào hàng đợi RabbitMQ mà không qua bước lưu trữ âm thanh hay gọi `voice-worker`.
3. **Phòng vệ cách ly dữ liệu**:
   - Khi nhân viên gọi danh sách phiên `GET /api/analysis` hoặc xem stats thống kê `GET /api/analysis/stats`, service/repository sẽ áp dụng bộ lọc nghiêm ngặt `owner_id = current_user.id`. Đảm bảo nhân viên này không thể xem trộm dữ liệu phân tích của nhân viên khác.
4. **Quyền hạn quản trị (Admin RBAC)**:
   - Các API quản trị dưới prefix `/api/admin/` yêu cầu tài khoản phải có vai trò `admin`. Admin có thể lấy danh sách toàn bộ nhân viên kèm hiệu năng tổng quát, kích hoạt/vô hiệu hóa tài khoản, đổi vai trò hoặc xem chi tiết biểu đồ Dashboard/Lịch sử làm việc của bất kỳ nhân viên nào.

---

## ⚡ Cơ Chế Caching Nâng Cao & Tối Ưu Hóa Hiệu Năng

Dịch vụ Backend tích hợp chặt chẽ bộ nhớ đệm **Redis** để giảm tải tối đa cho cơ sở dữ liệu PostgreSQL và mang lại phản hồi UI cực nhanh (dưới 1ms):

### 1. Cơ chế Caching Trạng thái Job Tức thời (Pending Job Caching)
* **Vấn đề**: Khi người dùng gửi file ghi âm hoặc văn bản phân tích, hệ thống đẩy Job vào RabbitMQ xử lý nền. Trong thời gian chờ Worker bắt đầu chạy, Frontend thực hiện **Polling (truy vấn lặp mỗi 2 giây)** để lấy trạng thái. Nếu không có cache, mỗi lượt Polling sẽ kích hoạt một truy vấn SQL đắt đỏ vào ổ đĩa.
* **Giải pháp**: Ngay khi tạo Job, API `submit_audio_analysis` hoặc `submit_text_analysis` lập tức ghi đè trạng thái `pending` của Job đó vào Redis cache (`cache:user:{owner_id}:analysis:{job_id}`) với TTL 1 giờ. Lượt Polling đầu tiên từ Frontend sẽ trúng cache 100%, đưa tải SQL Polling ban đầu về tuyệt đối **0%**.

### 2. Mô hình Cache-Aside cho Thống kê Dashboard (Dashboard Stats Caching)
* **Vấn đề**: Endpoint `/api/analysis/stats` tính toán các dữ liệu tổng hợp rất nặng (gom nhóm sentiment, tính điểm trung bình nhân viên, biểu đồ xu hướng 7 ngày). Truy vấn trực tiếp vào PostgreSQL khi lượng bản ghi lớn sẽ làm nghẽn cổ chai hệ thống.
* **Giải pháp**: Áp dụng mô hình **Cache-Aside**:
  1. Khi nhận request `GET /api/analysis/stats`, Backend kiểm tra cache Redis khóa `cache:user:{owner_id}:stats`.
  2. **Cache Hit**: Trả về dữ liệu JSON lưu trong cache lập tức (Latency < 1ms).
  3. **Cache Miss**: Thực hiện truy vấn aggregate gom nhóm trên PostgreSQL, ghi đền kết quả vào Redis với thời gian sống **24 giờ (TTL 86400 giây)**, và trả về cho client.

### 3. Thu hồi và Xóa bỏ Cache Chủ động (Active Cache Invalidation)
Để tránh dữ liệu cũ (stale data) hiển thị sai lệch trên Dashboard, Backend chủ động thực hiện thu hồi cache:
* **Khi xóa phiên (`DELETE /api/analysis/{job_id}`)**:
  * Xóa bản ghi trong PostgreSQL.
  * Xóa file âm thanh vật lý trong MinIO.
  * Lập tức gọi `cache.delete(job_id, owner_id)` để xóa cache trạng thái job.
  * Lập tức gọi `cache.delete_stats(owner_id)` để xóa cache stats. Khi người dùng quay lại Dashboard, hệ thống sẽ tự động tính toán lại dữ liệu sạch từ Postgres và ghi đè cache stats mới.

---

## Danh Sách API Công Khai (Endpoints)

Dịch vụ backend chạy trên cổng nội bộ `8000` của container và được Reverse Proxy Nginx trỏ cổng `9090` trên host để định tuyến an toàn:

### 1. Phân hệ Xác thực (Authentication)
| Method | Path | Quyền hạn | Mục đích |
|---|---|---|---|
| POST | `/api/auth/register` | Công khai | Đăng ký tài khoản nhân viên mới (mặc định chờ kích hoạt) |
| POST | `/api/auth/login` | Công khai | Đăng nhập và nhận mã JWT Token bảo mật |

### 2. Phân hệ Phân tích & Thống kê cá nhân
| Method | Path | Quyền hạn | Mục đích |
|---|---|---|---|
| POST | `/api/analysis/audio` | Nhân viên/Admin| Tải file ghi âm cuộc gọi lên MinIO & gửi vào hàng đợi RabbitMQ |
| POST | `/api/analysis/text` | Nhân viên/Admin| Gửi trực tiếp văn bản hội thoại để phân tích cảm xúc |
| GET | `/api/analysis` | Nhân viên/Admin| Lấy danh sách lịch sử phiên cá nhân (phân trang) |
| GET | `/api/analysis/{job_id}` | Nhân viên/Admin| Lấy kết quả phân tích chi tiết của một phiên thuộc sở hữu cá nhân |
| PATCH | `/api/analysis/{job_id}` | Nhân viên/Admin| Đổi tên phiên làm việc cá nhân |
| DELETE| `/api/analysis/{job_id}` | Nhân viên/Admin| Xoá phiên, xóa file MinIO vật lý và dọn dẹp Redis cache |
| GET | `/api/analysis/stats` | Nhân viên/Admin| Tổng hợp chỉ số hiệu suất cá nhân hiển thị lên Dashboard |

### 3. Phân hệ Quản trị (Admin Operations)
| Method | Path | Quyền hạn | Mục đích |
|---|---|---|---|
| GET | `/api/admin/employees` | Chỉ Admin | Lấy danh sách nhân viên kèm hiệu năng, điểm số và sentiment |
| GET | `/api/admin/employees/{id}/stats` | Chỉ Admin | Xem Dashboard thống kê chi tiết của một nhân viên cụ thể |
| GET | `/api/admin/employees/{id}/sessions`| Chỉ Admin | Xem danh sách lịch sử phiên làm việc của một nhân viên cụ thể |
| GET | `/api/admin/users` | Chỉ Admin | Lấy danh sách tất cả các tài khoản hệ thống để duyệt duyệt |
| PATCH | `/api/admin/users/{id}/status` | Chỉ Admin | Kích hoạt (Duyệt) hoặc Vô hiệu hóa một tài khoản người dùng |
| PATCH | `/api/admin/users/{id}/role` | Chỉ Admin | Thay đổi vai trò (quyền hạn) của một tài khoản (`admin` <-> `employee`) |
| GET | `/api/admin/metrics` | Chỉ Admin | Lấy metrics hệ thống tổng hợp (từ Prometheus API, được cache 10 giây trên Redis) |

### 4. Observability nội bộ
| Method | Path | Quyền hạn | Mục đích |
|---|---|---|---|
| GET | `/metrics` | Nội bộ Docker | Prometheus scrape HTTP metrics, auth events và phân tích của dịch vụ backend này. |

---

## Quản lý Cơ sở Dữ liệu (Alembic Migrations)

Cấu trúc cơ sở dữ liệu được quản lý tự động hoàn toàn bằng **Alembic**. Khi khởi tạo container backend, tập lệnh khởi chạy sẽ gọi lệnh di cư tự động lên phiên bản mới nhất (`head`) trước khi uvicorn khởi động.

Dự án sử dụng tệp di cư hợp nhất:
* `0001_initial_schema.py`: Thực hiện thiết lập đồng thời tất cả các bảng dữ liệu liên quan (`roles`, `users`, `user_role`, `analysis_jobs`, `analysis_results`), thiết lập ràng buộc khóa ngoại bảo vệ dữ liệu, đồng thời tự động chèn dữ liệu mẫu (Seed Data) bao gồm 2 vai trò mặc định và tài khoản quản trị viên tối cao ban đầu (`admin` / `admin123`).

---

## Cấu Hình Tập Trung & Bảo Mật Triển Khai

> [!IMPORTANT]
> - **Cấu hình tập trung Master `.env`**: Backend được nạp toàn bộ cấu hình (kết nối database, redis, rabbitmq, minio, cors) từ duy nhất tệp `.env` chung ở thư mục root thông qua cơ chế ánh xạ biến của `docker-compose.yml`. Đảm bảo Docker Image của backend là hoàn toàn bất biến (Stateless & Immutable), không chứa bất kỳ mật khẩu hay khóa bảo mật nhạy cảm nào khi được upload lên các registries (Docker Hub).
> - **Bức tường lửa Nginx**: Cổng `8000` của container backend hoàn toàn ẩn giấu, chỉ cho phép nhận các kết nối chuyển tiếp nội bộ từ reverse proxy Nginx. Giúp bảo vệ hệ thống tuyệt đối trước các đợt tấn công quét cổng và xâm nhập API trực tiếp.

