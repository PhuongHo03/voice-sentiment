# Lộ trình phát triển dự án Voice Sentiment

| Hạng mục | Trạng thái hiện tại |
|---|---|
| **Giai đoạn hiện tại** | ✅ Giai đoạn 2 — Loại bỏ hoàn toàn Mock, tích hợp local Whisper và remote LLM thực tế |
| **Giai đoạn tiếp theo** | ⏳ Giai đoạn 3 — Viết unit/integration tests và ổn định hóa hệ thống |
| **Thư mục gốc workspace** | `D:\voice-sentiment` |

## Cấu trúc Dự án

```text
backend/                  ← FastAPI API Gateway, điều phối công việc và migrations DB bằng Alembic
worker/                   ← Dịch vụ xử lý AI nền với FFmpeg, local Whisper, và LLM clients (OpenAI-compatible)
frontend/                 ← Giao diện Dashboard React/Vite
docs/explanations/        ← Thư mục tài liệu giải thích chi tiết các khu vực
docker-compose.yml        ← Tệp cấu hình khởi chạy toàn bộ hạ tầng dịch vụ cục bộ
nginx.conf                ← File cấu hình Proxy ngược Nginx cục bộ
```

## Các công nghệ vận hành (Runtime stack)

- **PostgreSQL**: Lưu trữ thông tin bền vững công việc (jobs) và kết quả phân tích cuộc gọi thoại.
- **MinIO**: Lưu trữ tệp tin đối tượng cho các file âm thanh ghi âm tải lên.
- **Redis**: Bộ nhớ đệm cache nhanh trạng thái và kết quả công việc.
- **RabbitMQ**: Bộ trung chuyển hàng đợi công việc từ Backend sang Worker.
- **Nginx**: Proxy ngược cục bộ (hiện đang mở cổng truy cập host tại `8082`).
- **Adminer**: Công cụ quản trị cơ sở dữ liệu PostgreSQL trực quan trên web (cổng `8083`).
- **Redis Insight**: Công cụ quản trị bộ nhớ đệm Redis trực quan trên web (cổng `8084`).
- **local Whisper (Internal)**: Dịch vụ nhận diện giọng nói tiếng Việt STT cục bộ chạy trên CPU (bằng thư viện `faster-whisper` lượng tử hóa `int8`).
- **LLM (External)**: Đầu cuối mô hình LLM tương thích OpenAI (ví dụ vLLM chạy tại địa chỉ IP của bạn hoặc các dịch vụ đám mây khác) để tóm tắt và đánh giá sắc thái cảm xúc.

## Danh sách công việc tiếp theo (Next work)

- [x] Chuyển đổi và đấu nối thành công mô hình nhận diện giọng nói tiếng Việt cục bộ bằng `faster-whisper` trên CPU của Worker.
- [x] Đấu nối đầu cuối mô hình LLM bên ngoài và xác minh cổng API phân tích văn bản thực tế.
- [x] Tích hợp bộ chuẩn hóa âm thanh (Audio normalization) cho các tệp ghi âm WebM trực tiếp từ Microphone trình duyệt sử dụng FFmpeg chạy tiến trình con (không tốn tài nguyên đĩa).
- [x] Thiết lập hệ thống di cư cơ sở dữ liệu di động (Database Migrations) bằng Alembic và tự động áp dụng khi khởi chạy Backend.
- [x] Loại bỏ hoàn toàn 100% tất cả mã nguồn liên quan đến giả lập "Mock" trong dự án.
- [x] Chuẩn hóa toàn bộ các biến cấu hình hệ thống: `RIVA_*` thành `VOICE_*` và `VLLM_*` thành `LLM_*`.
- [ ] Xây dựng bộ unit/integration tests tập trung cho backend, worker và frontend sau khi các giao thức đầu cuối hoạt động ổn định.

## Giai đoạn 1 — MVP scaffold

> Trạng thái: **Hoàn thành (Completed)**
> Tài liệu đọc thêm cho các phiên sau: Xem [backend-explanation.md](file:///d:/voice-sentiment/docs/explanations/backend-explanation.md), [worker-explanation.md](file:///d:/voice-sentiment/docs/explanations/worker-explanation.md), [frontend-explanation.md](file:///d:/voice-sentiment/docs/explanations/frontend-explanation.md), và [infrastructure-explanation.md](file:///d:/voice-sentiment/docs/explanations/infrastructure-explanation.md).

Phạm vi triển khai:
- Chia nhỏ cấu trúc thư mục Clean Architecture cho cả backend và worker.
- Dựng giao diện Dashboard React thô cho phép tải file, ghi âm microphone, gửi test nhanh văn bản và polling cập nhật.
- Dựng file compose điều phối PostgreSQL, MinIO, Redis, RabbitMQ, Nginx, backend, worker, frontend cục bộ.
- Thiết lập quyền sở hữu file cấu hình môi trường mẫu `.env.example` riêng biệt cho từng service.

## Giai đoạn 2 — Tích hợp ASR/LLM thực tế & Loại bỏ hoàn toàn Mock Fallback

> Trạng thái: **Hoàn thành (Completed)**
> Tài liệu đọc thêm cho các phiên sau: Xem [backend-explanation.md](file:///d:/voice-sentiment/docs/explanations/backend-explanation.md), [worker-explanation.md](file:///d:/voice-sentiment/docs/explanations/worker-explanation.md), [frontend-explanation.md](file:///d:/voice-sentiment/docs/explanations/frontend-explanation.md), và [infrastructure-explanation.md](file:///d:/voice-sentiment/docs/explanations/infrastructure-explanation.md).

Phạm vi triển khai:
- Loại bỏ hoàn toàn Riva STT và thay bằng mô hình **local `faster-whisper` (CPU int8)**, tích hợp bộ giải mã `ffmpeg` trực tiếp vào Docker image của Worker.
- Xây dựng bộ chuẩn hóa âm thanh tự động chuyển đổi mọi tệp tin đầu vào (webm, mp3, wav) thành linear PCM, mono, 16kHz, 16-bit WAV bytes cực kỳ mượt mà.
- Thiết lập kết nối LLM thực tế thông qua các biến cấu hình `LLM_*` trỏ trực tiếp đến mô hình tương thích với OpenAI bên ngoài.
- Dọn dẹp 100% tất cả logic kiểm tra mock, xóa bỏ các cuộc hội thoại mock giả lập và biến cấu hình mock dư thừa.
- Đổi tên toàn bộ hệ thống biến liên quan đến Riva thành `VOICE` (như `VOICE_SERVER_URI`, `VOICE_LANGUAGE_CODE`) và các biến vLLM thành `LLM` (như `LLM_BASE_URL`, `LLM_MODEL`).
- Cấu hình logs thời gian thực không đệm (`PYTHONUNBUFFERED=1` và `logging.basicConfig`) giúp quản trị container dễ dàng qua Docker logs.
- Tích hợp thành công Alembic quản lý di cư cơ sở dữ liệu cho PostgreSQL, tự động cập nhật schema lên phiên bản mới nhất `0001` khi bắt đầu chạy.
