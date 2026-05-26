# Tài liệu giải thích Hạ tầng (Infrastructure)

## Mục đích

Hạ tầng vận hành của toàn bộ hệ thống được khai báo tập trung và tối ưu hóa trong tệp tin `docker-compose.yml` nằm ở thư mục gốc của dự án. Hệ thống được thiết kế theo mô hình microservices cô lập mạng nội bộ, chia sẻ liên thông qua Docker bridge network, và chỉ mở các cổng quản trị cần thiết ra máy chủ (host) để bảo mật tối đa.

---

## Danh Sách Các Cổng Dịch Vụ Trên Host (Unified Port Mapping)

Để dễ dàng quản lý và tránh xung đột cổng trên máy chủ phát triển, toàn bộ các cổng UI quản trị, bảng điều khiển (Console) và ngõ vào API đều được quy hoạch đồng bộ vào dải cổng liên tục từ **`9090` đến `9095`**:

| Dịch vụ Container | Cổng Host | Cổng Container | Phạm vi / Mục đích |
|:---|:---:|:---:|:---|
| **Nginx Proxy** | **`9090`** | `80` | **Ngõ vào duy nhất** cho giao diện Frontend UI và API Backend |
| **Adminer** | **`9091`** | `8080` | Trình quản trị cơ sở dữ liệu PostgreSQL trực quan trên Web |
| **MinIO Console** | **`9092`** | `9001` | Trang quản trị giao diện (Console) bộ lưu trữ đối tượng S3 |
| **RedisInsight** | **`9093`** | `8001` | Giao diện giám sát bộ nhớ đệm nhanh Redis |
| **RabbitMQ Admin** | **`9094`** | `15672` | Trang quản trị hàng đợi công việc (RabbitMQ Management) |
| **`voice-worker` API** | **`9095`** | `8000` | FastAPI Web Server cung cấp API giải mã ASR/STT độc lập |

Các cổng giao thức kỹ thuật tiêu chuẩn của hạ tầng vẫn được giữ nguyên mặc định để phục vụ các kết nối client bên ngoài (như DBeaver, Redis CLI, S3 SDK, v.v.):
*   **PostgreSQL**: Cổng **`5432`**
*   **Redis**: Cổng **`6379`**
*   **MinIO S3 API**: Cổng **`9000`**
*   **RabbitMQ Protocol**: Cổng **`5672`**

---

## 🔒 Cô Lập Ứng Dụng Nghiệp Vụ (Application Hiding & Security)

> [!CAUTION]
> **Core Isolation**: Nhằm tuân thủ nguyên tắc bảo mật thông tin trong môi trường phân tán doanh nghiệp, cổng truy cập trực tiếp của hai dịch vụ ứng dụng cốt lõi:
> 1.  **`backend`** (`8000`)
> 2.  **`frontend`** (`5173`)
>
> đã bị **loại bỏ hoàn toàn khỏi khai báo ánh xạ cổng (ports mapping) ra host** trong tệp `docker-compose.yml`. Mọi nỗ lực truy cập trực tiếp vào các dịch vụ này từ máy khách đều bị chặn đứng ở tầng mạng Docker. Mọi lưu lượng truy cập bắt buộc phải đi qua **Nginx Gateway (cổng `9090`)** để được định tuyến an toàn.

---

## Luồng Dữ Liệu Hạ Tầng (Flow)

```text
[Trình duyệt] ──► (Cổng 9090) Nginx Proxy
                        │
                        ├──► [frontend:5173]  (Tải giao diện Dashboard React)
                        └──► [backend:8000]   (Giao dịch API nghiệp vụ)
                                  │
                                  ├──► [PostgreSQL:5432]  (Đọc/Ghi Jobs, Results, agent_score)
                                  ├──► [MinIO:9000]       (Lưu tệp tin âm thanh uploads)
                                  ├──► [Redis:6379]       (Bộ nhớ đệm đọc kết quả nhanh)
                                  └──► [RabbitMQ:5672]    (Đẩy tin nhắn Jobs vào hàng đợi)
                                            │
                                            └──► [llm-worker]  (Consumes Jobs không cổng)
                                                     │
                                                     ├──► [MinIO:9000]         (Tải audio gốc)
                                                     ├──► [voice-worker:8000]  (HTTP POST giải mã ASR)
                                                     ├──► [Remote LLM:8007]    (HTTP POST phân tích + đánh giá nhân viên)
                                                     └──► Ghi kết quả vào Postgres & Redis cache
```

---

## Hướng Dẫn Sử Dụng RabbitMQ Management UI

Truy cập `http://localhost:9094` với tài khoản `guest` / `guest`.

| Mục | Nơi kiểm tra | Ý nghĩa |
|---|---|---|
| **Queues** → `analysis.jobs` | Tab "Queues" | Xem số tin nhắn đang chờ (Ready), đang xử lý (Unacked), và tổng (Total) |
| **Messages** | Nút "Get messages" trong queue | Xem nội dung raw của từng tin nhắn trong hàng đợi |
| **Connections** | Tab "Connections" | Xem kết nối từ `llm-worker` tới RabbitMQ |
| **Channels** | Tab "Channels" | Xem channel consumer đang lắng nghe |

> [!TIP]
> Nếu cột **Unacked > 0** kéo dài mà không giảm về 0, có thể `llm-worker` đang xử lý nhưng bị treo. Kiểm tra log bằng `docker compose logs -f llm-worker` để xác định nguyên nhân.

---

## Công Cụ Giám Sát & Quản Trị

| Công cụ | URL | Tài khoản | Mục đích |
|---|---|---|---|
| **Nginx Gateway** | http://localhost:9090 | — | Frontend UI + API routing |
| **Adminer** | http://localhost:9091 | postgres/postgres | Quản trị DB trực quan |
| **MinIO Console** | http://localhost:9092 | minioadmin/minioadmin | Xem/xoá file âm thanh |
| **RedisInsight** | http://localhost:9093 | — | Giám sát keys Redis cache |
| **RabbitMQ** | http://localhost:9094 | guest/guest | Giám sát hàng đợi công việc |
| **voice-worker API** | http://localhost:9095/docs | — | Swagger docs ASR API |

---

## Các Lệnh Vận Hành Hạ Tầng

```powershell
# Kiểm tra file cấu hình Docker Compose hoạt động và phân tách đúng cú pháp
docker compose config

# Khởi chạy và biên dịch lại toàn bộ hạ tầng (bao gồm cả voice-worker và llm-worker)
docker compose up -d --build

# Chỉ rebuild một dịch vụ cụ thể (nhanh hơn)
docker compose up --build -d backend
docker compose up --build -d llm-worker
docker compose up --build -d frontend

# Kiểm tra log thời gian thực của cụm microservices xử lý AI nền
docker compose logs -f voice-worker llm-worker

# Kiểm tra trạng thái tất cả containers
docker compose ps

# Dừng và xoá toàn bộ hạ tầng (giữ lại volumes DB)
docker compose down

# Xoá hoàn toàn bao gồm volumes (reset DB)
docker compose down -v
```
