# Tài liệu giải thích Backend

## Mục đích

Thư mục `backend/` chứa dịch vụ FastAPI giao tiếp trực tiếp với giao diện người dùng (UI-facing API). Dịch vụ này đảm nhận các nhiệm vụ: quản lý các API công khai, xác thực yêu cầu (validation), lưu trữ thông tin trạng thái (metadata), tải tệp tin lên bộ lưu trữ MinIO, xuất bản (publish) công việc vào hàng đợi RabbitMQ, và truy vấn trạng thái/kết quả từ Redis hoặc PostgreSQL. Backend hoàn toàn **không** gọi trực tiếp các dịch vụ chuyển giọng nói (ASR) hay mô hình LLM để giữ cho API luôn nhẹ và phản hồi nhanh.

## Cấu trúc thư mục

```text
backend/
├── app/main.py                         ← Điểm khởi chạy FastAPI và chạy migrations DB tự động
├── app/core/config.py                  ← Cấu hình môi trường cho Backend
├── app/domain/analysis.py              ← Định nghĩa các kiểu dữ liệu Domain của Job/Result
├── app/application/use_cases/          ← Use cases gửi công việc phân tích âm thanh/văn bản
├── app/infrastructure/database/        ← Khởi tạo SQLAlchemy models/session/repository
├── app/infrastructure/storage/         ← Bộ điều hợp tải tệp tin âm thanh lên MinIO
├── app/infrastructure/cache/           ← Bộ điều hợp đọc nhanh trạng thái công việc từ Redis
├── app/infrastructure/queue/           ← Bộ điều hợp xuất bản công việc vào hàng đợi RabbitMQ
└── app/interfaces/controllers/         ← Các bộ điều khiển HTTP (Health và Analysis)
```

## Luồng chạy hệ thống (Runtime flow)

1. **Phân tích âm thanh**: Khi gọi `POST /api/analysis/audio`, Backend sẽ lưu tệp tin âm thanh vào MinIO, tạo một bản ghi trạng thái trong bảng `analysis_jobs` của PostgreSQL, xuất bản một tin nhắn chứa ID công việc vào hàng đợi `analysis.jobs` của RabbitMQ, sau đó trả về ngay lập tức cho Frontend mã `job_id` và trạng thái `pending`.
2. **Phân tích văn bản**: Khi gọi `POST /api/analysis/text`, Backend tạo một bản ghi công việc dạng văn bản và đẩy trực tiếp tin nhắn kèm nội dung văn bản vào cùng hàng đợi RabbitMQ.
3. **Tra cứu kết quả**: Khi gọi `GET /api/analysis/{job_id}`, Backend sẽ truy vấn bộ nhớ đệm **Redis** trước để phản hồi nhanh nhất. Nếu không thấy, nó sẽ tìm trong cơ sở dữ liệu **PostgreSQL**. Khi công việc hoàn thành (`completed`), kết quả trả về sẽ bao gồm: đoạn hội thoại (transcript), danh sách tóm tắt (summary), sắc thái cảm xúc cuộc gọi (sentiment), lý do đánh giá sắc thái (sentiment_reason), và điểm số tự tin (confidence).

## Các cổng dịch vụ công khai (Endpoints)

| Phương thức | Đường dẫn | Mục đích |
|---|---|---|
| GET | `/health` | Kiểm tra tình trạng hoạt động (health check) của Backend |
| POST | `/api/analysis/audio` | Tải lên file âm thanh (`.mp3`, `.wav`, hoặc `.webm` từ trình duyệt) để phân tích |
| POST | `/api/analysis/text` | Gửi trực tiếp văn bản để phân tích nhanh |
| GET | `/api/analysis/{job_id}` | Lấy trạng thái và kết quả phân tích công việc |

## Cấu hình môi trường (Env)

File `backend/.env.example` định nghĩa cấu hình kết nối tới PostgreSQL, Redis, RabbitMQ, MinIO, và danh sách các cổng CORS được phép truy cập (`CORS_ORIGINS`).

## Quản lý di cư cơ sở dữ liệu (Database Migrations - Alembic)

Dịch vụ backend trực tiếp quản lý cấu trúc bảng trong PostgreSQL bằng **Alembic**. Khi khởi chạy container, Backend sẽ tự động chạy các tệp tin di cư cơ sở dữ liệu (`command.upgrade(cfg, "head")`) để đảm bảo các bảng dữ liệu được tạo và cập nhật tự động.
Các file cấu hình và kịch bản di cư được lưu trữ lần lượt tại `backend/alembic.ini` và `backend/alembic/versions/`.

*Tài liệu phản ánh trạng thái backend tại giai đoạn hoàn thành Giai đoạn 2.*
