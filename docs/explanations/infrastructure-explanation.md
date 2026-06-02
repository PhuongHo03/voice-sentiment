# Tài liệu giải thích Hạ tầng (Infrastructure)

## Mục đích

Hạ tầng vận hành của toàn bộ hệ thống được khai báo tập trung, nhất quán và tối ưu hóa trong tệp tin `docker-compose.yml` nằm ở thư mục gốc của dự án. Hệ thống được thiết kế theo mô hình microservices cô lập mạng nội bộ (Internal Bridge Network), bảo mật đa tầng, phân tách dữ liệu người dùng cô lập (Tenant-Isolation) và được quản lý cấu hình thông qua duy nhất một tệp tin Master `.env` đặt ở root dự án theo chuẩn thiết kế **12-Factor App**.

---

## Danh Sách Các Cổng Dịch Vụ Trên Host (Unified Port Mapping)

Để dễ dàng quản lý và tránh xung đột cổng trên máy chủ phát triển, các cổng UI quản trị, bảng điều khiển (Console) và ngõ vào web chính được quy hoạch quanh dải **`9090` đến `9095`**; Prometheus chỉ hoạt động nội bộ trong Docker Network và được truy cập an toàn qua phân hệ quản trị của Backend:

| Dịch vụ Container | Cổng Host | Cổng Container | Phạm vi / Mục đích |
|:---|:---:|:---:|:---|
| **Nginx Proxy** | **`9090`** | `80` | **Ngõ vào duy nhất** cho giao diện Frontend UI và API Backend |
| **Adminer** | **`9091`** | `8080` | Trình quản trị cơ sở dữ liệu PostgreSQL trực quan trên Web |
| **MinIO Console** | **`9092`** | `9001` | Trang quản trị giao diện (Console) bộ lưu trữ đối tượng S3 |
| **RedisInsight** | **`9093`** | `5540` | Giao diện giám sát bộ nhớ đệm nhanh Redis |
| **RabbitMQ Admin** | **`9094`** | `15672` | Trang quản trị hàng đợi công việc (RabbitMQ Management) |
| **`voice-worker` API** | **`9095`** | `8000` | FastAPI Web Server cung cấp API giải mã ASR/STT độc lập |

Các cổng giao thức kỹ thuật tiêu chuẩn của hạ tầng vẫn được giữ nguyên mặc định để phục vụ các kết nối client bên ngoài (như DBeaver, Redis CLI, S3 SDK, v.v.):
*   **PostgreSQL**: Cổng **`5432`**
*   **Redis**: Cổng **`6379`**
*   **MinIO S3 API**: Cổng **`9000`**
*   **RabbitMQ Protocol**: Cổng **`5672`**

---

## 🔒 Cơ Chế Bảo Mật & Cô Lập (Security & Isolation)

Hệ thống áp dụng các tiêu chuẩn an toàn thông tin chuyên nghiệp (Production-Grade Security):

### 1. Cô lập Ứng dụng Nghiệp vụ (Application Hiding)
> [!CAUTION]
> **Core Isolation**: Nhằm tuân thủ nguyên tắc bảo mật thông tin, cổng truy cập trực tiếp của hai dịch vụ ứng dụng cốt lõi:
> 1.  **`backend`** (`8000`)
> 2.  **`frontend`** (`5173`)
>
> đã bị **loại bỏ hoàn toàn khỏi khai báo ánh xạ cổng (ports mapping) ra host** trong tệp `docker-compose.yml`. Mọi nỗ lực truy cập trực tiếp vào các dịch vụ này từ máy khách đều bị chặn đứng ở tầng mạng Docker. Mọi lưu lượng truy cập bắt buộc phải đi qua **Nginx Gateway (cổng `9090`)** để được định tuyến an toàn và xử lý CORS tự động.

### 2. Cách ly Dữ liệu Người dùng (Tenant Isolation - Phase 6)
Để đảm bảo quyền riêng tư tuyệt đối cho dữ liệu của từng tài khoản nhân viên thường và admin:
* **Cô lập Lưu trữ đối tượng (MinIO/S3)**: File âm thanh ghi âm gốc được tải lên theo cấu trúc đường dẫn chứa ID người dùng (`owner_id`):
  `uploads/{owner_id}/{filename}`
  Điều này ngăn chặn chéo quyền truy cập ở tầng lưu trữ vật lý S3.
* **Cách ly Bộ nhớ đệm (Redis Key Namespacing & Virtual Folders)**:
  Các khóa cache Redis của từng người dùng được phân tách và cấu trúc hóa cực kỳ chuyên nghiệp bằng dấu hai chấm (`:`), giúp các giao diện trực quan như RedisInsight tự động phân cấp thành các thư mục ảo:
  * **Trạng thái Job Phân tích**: `cache:user:{owner_id}:analysis:{job_id}`
    * Nằm trong thư mục ảo `analysis/` của từng người dùng.
    * TTL: 1 giờ (`3600` giây) để tránh tràn bộ nhớ đệm.
  * **Thống kê Dashboard**: `cache:user:{owner_id}:stats`
    * Nằm bên ngoài thư mục ảo `analysis/` nhưng cùng trong thư mục của người dùng `{owner_id}`, giữ cấu trúc phẳng gọn gàng cho stats tổng quan.
    * TTL: 24 giờ (`86400` giây) vì đây là các truy vấn gom nhóm PostgreSQL cực kỳ đắt đỏ (`COUNT`, `AVG`).
  
  **Chiến lược Caching & Invalidation Nâng cao (Advanced Caching Strategy)**:
  1. **Pending Job Caching (Triệt tiêu PostgreSQL Polling 100%)**: Khi người dùng gửi file ghi âm hoặc văn bản, API Backend lập tức tạo bản ghi database và ghi đè trạng thái `pending` vào Redis. Trình duyệt gửi request polling kiểm tra trạng thái sẽ trúng cache ngay lập tức (Cache Hit 100%) ở luồng thăm dò đầu tiên, triệt tiêu hoàn toàn gánh nặng truy vấn database đĩa cứng đắt đỏ.
  2. **Dashboard Stats Caching**: Cache toàn bộ dữ liệu biểu đồ tròn, cột, phân bổ điểm số và xu hướng trong 24 giờ.
  3. **Thu hồi Cache Thông minh (Smart Invalidation)**: Stats cache được tự động xóa bỏ (evict) thông qua 2 đầu mối sự kiện:
     * **llm-worker**: Khi một tác vụ phân tích hoàn thành thành công và lưu kết quả vào PostgreSQL, worker lập tức xóa key stats cache của user sở hữu để các biểu đồ trên UI được cập nhật dữ liệu mới nhất tức thì.
     * **backend**: Khi người dùng nhấn nút xóa một phiên hội thoại, API Gateway thực hiện xóa phiên trong Postgres, xóa file trong MinIO, xóa job cache trong Redis và đồng thời xóa stats cache của user để cập nhật lại Dashboard.

### 3. Phân phối Đa hàng đợi linh hoạt (RabbitMQ Multi-Queue)
Hệ thống nâng cấp từ 1 hàng đợi đơn lẻ lên mô hình **Đa hàng đợi song song** được điều phối động thông qua cấu hình biến môi trường `RABBITMQ_QUEUE_COUNT=2` đặt tại tệp `.env` root. Giúp hệ thống dễ dàng nâng cấu hình mở rộng (scaling) số lượng worker khi tải thực tế tăng cao.

---

## Cấu Hình Tập Trung Master `.env` (Chuẩn 12-Factor App)

Toàn bộ hệ thống microservices được cấu hình thông qua **duy nhất một tệp tin [`.env`](file:///d:/voice-sentiment/.env) đặt ở thư mục gốc của dự án**. File mẫu duy nhất là root `.env.example`; các `.env`/`.env.example` cục bộ trong `backend/`, `frontend/`, `llm-worker/`, `voice-worker/` đã được dọn bỏ để tránh cấu hình phân mảnh.

### Cách hoạt động:
1. Khi thực thi lệnh `docker compose up`, Docker Compose sẽ đọc tệp `.env` ở root này để tự động điền các biến cấu hình (như `${POSTGRES_DB}`, `${MINIO_ROOT_USER}`) vào tệp `docker-compose.yml` (Interpolation).
2. Từng container (`backend`, `frontend`, `llm-worker`, `voice-worker`) được chỉ định nạp chung file `env_file: .env`. Hệ điều hành ảo của từng container sẽ nạp toàn bộ các biến cấu hình này.
3. Khi code ứng dụng (ví dụ Pydantic Settings của Python) khởi chạy, nó sẽ đọc trực tiếp từ môi trường hệ điều hành đã được nạp sẵn.
4. **Lợi ích**: Docker Images là hoàn toàn bất biến (Immutable) và sạch sẽ, không chứa thông tin cấu hình nhạy cảm. Bạn có thể tự tin đẩy các images lên Docker Hub công khai mà hoàn toàn không sợ bị lộ lọt mật khẩu hay API Keys.

---

## Luồng Dữ Liệu Hạ Tầng (Flow)

```text
[Trình duyệt] ──► (Cổng 9090) Nginx Proxy
                        │
                        ├──► [frontend:5173]      (Tải giao diện Dashboard React)
                        └──► [backend:8000]       (Giao dịch API nghiệp vụ có JWT)
                                   │
                                   ├──► [PostgreSQL:5432]  (Lưu dữ liệu cô lập: owner_id)
                                   ├──► [MinIO:9000]       (Lưu audio: uploads/{owner_id}/*)
                                   ├──► [Redis:6379]       (Cache riêng biệt: cache:user:{owner_id}/*)
                                   ├──► [RabbitMQ:5672]    (Đẩy tin nhắn Jobs vào Multi-Queue)
                                   └──► [prometheus:9090]  (Truy vấn metrics nội bộ + Redis cache 10s)
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
| **Queues** | Tab "Queues" | Xem danh sách các queues hoạt động (mặc định 2 queues). Xem số tin nhắn đang chờ (Ready) và đang xử lý (Unacked) |
| **Messages** | Nút "Get messages" trong queue | Xem nội dung raw của từng tin nhắn công việc trong hàng đợi |
| **Connections** | Tab "Connections" | Xem các kết nối từ `llm-worker` và `backend` tới RabbitMQ |

---

## Observability với Prometheus

- Cấu hình hạ tầng runtime được gom vào `infras/`: `infras/nginx.conf` cho reverse proxy và `infras/prometheus.yml` cho scrape jobs. Root `nginx.conf` đã được dọn bỏ; Docker Compose mount trực tiếp `./infras/nginx.conf`.
- Prometheus chủ động scrape metrics từ `backend:8000/metrics`, `voice-worker:8000/metrics`, `llm-worker:9100/metrics` và các exporter Postgres/Redis/RabbitMQ/Nginx.
- Frontend Admin gọi API `/api/admin/metrics` của Backend để lấy metrics tổng hợp hệ thống. API này được bảo vệ bởi lớp xác thực Admin của Backend, đồng thời sử dụng Redis cache 10 giây (`admin:metrics:snapshot`) để giảm tải các truy vấn lặp tới Prometheus.
- Prometheus API nằm hoàn toàn trong mạng nội bộ Docker và không bị phơi bày ra cổng public/Nginx.

---

## Công Cụ Giám Sát & Quản Trị

| Công cụ | URL | Tài khoản | Mục đích |
|---|---|---|---|
| **Nginx Gateway** | http://localhost:9090 | — | Giao diện Web + Định tuyến API |
| **Adminer** | http://localhost:9091 | postgres/postgres | Quản trị DB trực quan |
| **MinIO Console** | http://localhost:9092 | minioadmin/minioadmin | Xem/xoá file âm thanh |
| **RedisInsight** | http://localhost:9093 | — | Giám sát keys Redis cache |
| **RabbitMQ** | http://localhost:9094 | guest/guest | Giám sát hàng đợi công việc |
| **voice-worker API** | http://localhost:9095/docs | — | Swagger docs STT API |

---

## Các Lệnh Vận Hành Hạ Tầng

```powershell
# Chạy biên dịch và khởi chạy toàn bộ cụm hạ tầng với Master .env tập trung
docker compose up -d --build

# Xem log thời gian thực của cụm xử lý AI
docker compose logs -f voice-worker llm-worker

# Xem log thời gian thực của cổng ngõ API Gateway và DB
docker compose logs -f backend postgres

# Kiểm tra tình trạng hoạt động và cổng của các container
docker compose ps

# Dừng và xóa toàn bộ hạ tầng (giữ lại dữ liệu lưu trữ bền vững DB/MinIO)
docker compose down

# Xóa hoàn toàn bao gồm cả dữ liệu lưu trữ (Reset toàn hệ thống)
docker compose down -v
```
