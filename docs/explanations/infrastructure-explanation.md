# Tài liệu giải thích Hạ tầng (Infrastructure)

## Mục đích

Hạ tầng vận hành của dự án được khai báo toàn bộ trong file `docker-compose.yml` ở thư mục gốc. Dự án được thiết kế tinh gọn và cố ý không sử dụng thư mục cấu hình `infra/` riêng biệt.

## Các Dịch vụ (Services)

| Tên Dịch vụ | Cổng (Port) | Mục đích vận hành |
|---|---:|---|
| **PostgreSQL** | 5432 | Lưu trữ bền vững thông tin công việc (job) và kết quả phân tích |
| **MinIO** | 9000, 9001 | Lưu trữ đối tượng (Object Storage) cho các file âm thanh đầu vào và trang Console quản lý |
| **Redis** | 6379 | Bộ nhớ đệm (cache) truy vấn nhanh trạng thái và kết quả phân tích công việc |
| **RabbitMQ** | 5672, 15672 | Hàng đợi trung chuyển công việc (Broker) và trang quản lý Management UI |
| **Backend** | 8000 | API FastAPI công khai phục vụ giao tiếp giao diện |
| **Frontend** | 5173 | Máy chủ chạy thử nghiệm môi trường phát triển Vite |
| **Nginx** | 8082 | Cổng Proxy ngược (Reverse Proxy) điều hướng tích hợp cho Frontend/Backend (chuyển từ cổng gốc 8080 để tránh xung đột cổng trên máy chủ gốc) |
| **Adminer** | 8083 | Giao diện quản trị PostgreSQL trực quan trên nền Web |
| **Redis Insight** | 8084 | Giao diện quản trị Redis trực quan chính thức trên nền Web |


## Luồng dữ liệu hạ tầng (Flow)

Giao diện Frontend gọi API Backend thông qua cổng Nginx ngược (`8082`). Backend thực hiện lưu trữ file âm thanh đầu vào vào MinIO, ghi nhận thông tin công việc vào PostgreSQL, xuất bản tin nhắn công việc vào RabbitMQ, và cập nhật trạng thái cache nhanh sang Redis.
Dịch vụ Worker tiêu thụ hàng đợi RabbitMQ, tải file âm thanh tương ứng từ MinIO, cập nhật trạng thái vào PostgreSQL/Redis, và thực hiện chuyển đổi giọng nói bằng mô hình local Whisper kết hợp gửi phân tích văn bản tới mô hình LLM tương thích OpenAI bên ngoài.

## Các Lệnh Vận Hành Cơ Bản

```powershell
# Kiểm tra cấu hình Docker Compose hoạt động
docker compose config

# Khởi chạy và build lại toàn bộ hạ tầng cục bộ
docker compose up --build
```

*Tài liệu phản ánh trạng thái infrastructure tại giai đoạn hoàn thành Giai đoạn 2.*
