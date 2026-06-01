# Tài liệu giải thích hệ thống Worker (Decoupled Microservices)

## Mục đích

Để tối ưu hóa hiệu năng, tăng khả năng mở rộng (scale) và nâng cao tính tái sử dụng, hệ thống xử lý nền (background worker) của dự án được phân tách hoàn chỉnh thành hai dịch vụ microservices độc lập hoạt động cực kỳ ăn ý:

1. **`voice-worker` (Stateless ASR & Diarization Web Server)**: Dịch vụ FastAPI thuần túy nhận nhiệm vụ chuyển đổi giọng nói thành văn bản (Speech-to-Text) bằng mô hình `faster-whisper` chạy cục bộ trên CPU kết hợp với phân đoạn người nói (Speaker Diarization) sử dụng mô hình ONNX siêu nhẹ.
2. **`llm-worker` (RabbitMQ Orchestrator & Two-Pass LLM Client)**: Dịch vụ tiêu thụ tin nhắn từ hàng đợi RabbitMQ, điều phối quy trình tải file từ MinIO, gọi dịch vụ `voice-worker` để lấy văn bản hội thoại phân đoạn, thực hiện quy trình LLM 2 bước (Two-Pass LLM) để gán vai hội thoại chính xác và đánh giá nhân viên, sau đó lưu trữ kết quả vào PostgreSQL và Redis cache.

---

## Cấu trúc thư mục

```text
├── voice-worker/
│   ├── app/main.py                         ← Điểm khởi chạy FastAPI exposes cổng 8000 (Host: 9095)
│   ├── app/controllers/transcription_controller.py ← HTTP route POST /api/transcribe
│   ├── app/configs/config.py               ← Cấu hình môi trường qua Pydantic Settings
│   ├── app/configs/metrics.py              ← Prometheus /metrics, request/transcription counters và latency histograms
│   ├── app/services/transcription_service.py ← Điều phối file bytes → Whisper/Diarization → response
│   ├── app/ai/                             ← Các module AI cục bộ
│   │   ├── whisper_stt_client.py           ← FFmpeg audio normalization + faster-whisper inference
│   │   └── speaker_diarization.py          ← Phân đoạn người nói qua WeSpeaker ONNX + NumPy K-Means
│   ├── Dockerfile                          ← Cài đặt Python, FFmpeg, ONNX Runtime và các thư viện ASR
│   └── requirements.txt                    ← Thư viện hỗ trợ: fastapi, faster-whisper, onnxruntime, kaldi-native-fbank
│
├── llm-worker/
│   ├── app/main.py                         ← Điểm chạy nền lắng nghe RabbitMQ
│   ├── app/configs/config.py               ← Cấu hình kết nối tới DB, Cache, Queue, LLM và voice-worker
│   ├── app/configs/metrics.py              ← Embedded Prometheus metrics server cổng nội bộ 9100
│   ├── app/services/analyze_job.py         ← Service điều phối: audio/text → STT → LLM → DB/Cache
│   ├── app/repositories/analysis_repository.py ← SQLAlchemy repository lưu kết quả bền vững vào Postgres
│   ├── app/models/models.py                ← ORM models phản ánh bảng jobs/results/users liên quan
│   ├── app/ai/llm_client.py                ← Client gọi LLM bên ngoài với cơ chế Two-Pass (Role Mapping + Analysis)
│   ├── app/configs/database.py             ← Factory kết nối cơ sở dữ liệu
│   ├── app/configs/storage.py              ← S3 Client tải file âm thanh nguồn từ MinIO
│   ├── app/configs/cache.py                ← Redis Client cập nhật bộ nhớ đệm cache trạng thái công việc
│   ├── app/configs/queue.py                ← RabbitMQ consumer lắng nghe đa hàng đợi 'analysis.jobs'
│   └── Dockerfile                          ← Image siêu nhẹ chứa thư viện Python (không cần FFmpeg/Whisper)
```

---

## Phân tích Chi tiết Từng Dịch Vụ

### 1. `voice-worker` (Stateless ASR & Diarization)

* **Thiết kế Stateless**: Dịch vụ hoạt động độc lập và hoàn toàn không kết nối tới cơ sở dữ liệu Postgres, Redis hay hàng đợi RabbitMQ, đóng vai trò như một máy chủ API nội bộ cực kỳ an toàn.
* **API Đầu Vào**: Cung cấp API `POST /api/transcribe` nhận tệp âm thanh dạng multipart form-data.
* **Quy trình xử lý âm thanh**:
  1. **Chuẩn hóa Âm thanh (FFmpeg Normalization)**: Tệp ghi âm (như WebM Opus từ mic trình duyệt hoặc file MP3) sẽ được tự động chuyển đổi thông qua RAM pipe (không lưu xuống đĩa) thành định dạng chuẩn **Linear PCM, 1 Mono channel, 16kHz, 16-bit WAV** bằng công cụ FFmpeg subprocess.
  2. **Giải mã Chuyển văn bản (Whisper STT)**: Sử dụng mô hình `small` của `faster-whisper` tối ưu hóa chạy trực tiếp trên CPU với kiểu lượng tử hóa `int8` để giảm thiểu dung lượng RAM chiếm dụng.
  3. **Phân tách Người nói (WeSpeaker ONNX Diarization)**: 
     - Dịch vụ tự động tải mô hình WeSpeaker ResNet34 ONNX (~7 MB) trực tiếp từ Hugging Face CDN ở lần chạy đầu tiên.
     - Với mỗi phân đoạn câu thoại do Whisper giải mã, dịch vụ trích xuất 80-dim log-Mel filterbank và chạy inference ONNX Runtime để tính toán **vector nhúng đặc trưng giọng nói (256-dim speaker embedding)**.
     - Sau đó, hệ thống áp dụng thuật toán **K-Means Clustering (k=2) viết thuần túy bằng thư viện NumPy** (PyTorch-free & HuggingFace-gating-free) để chia nhóm các phân đoạn câu thoại thành `"Speaker 0"` và `"Speaker 1"`.

---

### 2. `llm-worker` (RabbitMQ Orchestrator & Two-Pass LLM)

* **Điều phối không đồng bộ (Orchestrator) & Quản lý Cache**: 
  Dịch vụ lắng nghe tin nhắn công việc từ đa hàng đợi RabbitMQ (`analysis.jobs`), tự động cập nhật trạng thái đồng thời lên Postgres và Redis cache riêng biệt của người dùng (`owner_id`) theo vòng đời:
  * **Processing**: Cập nhật trạng thái trong Redis thành `processing` ngay khi worker bắt đầu xử lý âm thanh.
  * **Completed**: Khi kết thúc thành công, lưu kết quả bền vững vào Postgres, đồng thời lưu kết quả vào Redis dưới khóa `cache:user:{owner_id}:analysis:{job_id}` giúp Frontend lấy ngay tức thì.
  * **Failed**: Nếu có lỗi xảy ra, ghi nhận lỗi vào database và cập nhật trạng thái cache thành `failed` kèm nội dung `error_message`.
  * **Xóa Stats Cache (Smart Invalidation)**: Khi Job hoàn thành thành công, `llm-worker` chủ động gọi `self.cache.delete_stats(owner_id)` để thu hồi cache thống kê cũ của người dùng. Lần tiếp theo người dùng truy cập giao diện Dashboard, Backend sẽ tính toán dữ liệu thống kê mới nhất (bao gồm cả job vừa hoàn thành) để hiển thị chính xác 100%.
* **Cơ chế gọi LLM 2 bước (Two-Pass LLM Analysis)**:
  Do kết quả phân tách giọng nói từ `voice-worker` trả về ở dạng nhãn nặc danh (`Speaker 0` và `Speaker 1`), `llm_client.py` sẽ thực thi luồng gọi LLM 2 bước thông minh:
  * **Pass 1: Semantic Role Mapping (Gán vai hội thoại)**:
    Gửi 10 lượt hội thoại đầu tiên làm excerpt lên LLM cùng định nghĩa nghiệp vụ. LLM sẽ phân tích ngữ cảnh giao tiếp (chào hỏi, hỏi thông tin, tư vấn...) để dịch nhãn nặc danh thành vai trò thực tế:
    `"Speaker 0" -> "Nhân viên"` và `"Speaker 1" -> "Khách hàng"` (hoặc ngược lại).
  * **Pass 2: Phân tích & Đánh giá (Full Analysis & Evaluation)**:
    Sau khi đã chuẩn hóa vai thoại, toàn bộ nội dung hội thoại hoàn chỉnh sẽ được gửi lên LLM để thực hiện phân tích tổng hợp: tóm tắt cuộc gọi (`summary`), sắc thái cảm xúc (`sentiment`), lý do đánh giá (`sentiment_reason`), điểm tự tin (`confidence`), đặc biệt là **chấm điểm kỹ năng CSKH của nhân viên** (`agent_score` từ 0-100đ) và **đưa ra các lời khuyên hành động thực tiễn** (`agent_advice`).

---

## Cấu trúc JSON Kết Quả Phân Tích

Mô hình LLM được ràng buộc nghiêm ngặt bằng Prompt Engineering để trả về định dạng JSON cấu trúc:

```json
{
  "summary": [
    "Khách hàng gọi điện phản ánh đơn hàng bị trễ hạn.",
    "Nhân viên đã xin lỗi và kiểm tra mã vận đơn hỗ trợ khách nhiệt tình."
  ],
  "sentiment": "positive | neutral | negative",
  "sentiment_reason": "Cuộc gọi ban đầu tiêu cực nhưng nhân viên đã khéo léo giải quyết giúp khách hàng vui vẻ trở lại.",
  "confidence": 0.95,
  "agent_score": 85,
  "agent_advice": [
    "Nên chủ động cung cấp thông tin giảm giá hoặc voucher bù đắp cho việc trễ đơn.",
    "Giữ vững tốc độ phản hồi nhanh nhẹn hiện tại."
  ]
}
```

---

## Xử Lý Lỗi & Độ Bền Bỉ (Resilience)

Hệ thống được chứng minh khả năng tự khôi phục và phục hồi kết nối ổn định thông qua test-suite Giai đoạn 7:

* **Tự kết nối lại (Auto Reconnect)**: Nếu kết nối mạng tới Postgres, Redis hoặc RabbitMQ bị đứt quãng, các driver (`pika`, `sqlalchemy`, `redis-py`) sẽ tự động rơi vào trạng thái chờ và kết nối lại khi hạ tầng online trở lại.
* **Bảo vệ luồng (Error Propagation)**: Mọi lỗi xảy ra (Timeout khi gọi STT, LLM trả về JSON lỗi, MinIO mất file) đều được bắt (`try-except`) để đánh dấu trạng thái Job là `failed` trên Postgres và Redis, đồng thời ghi nhận nội dung `error_message` phục vụ chẩn đoán, tránh gây crash hay treo container.

---

## Observability với Prometheus

- `voice-worker` expose `GET /metrics` trên cổng nội bộ `8000` để Prometheus scrape HTTP request metrics, transcription counters, upload size và transcription latency.
- `llm-worker` không phải HTTP API nghiệp vụ, nên khởi động embedded Prometheus HTTP server trên cổng nội bộ `9100`. Prometheus scrape `llm-worker:9100/metrics` để lấy job counters, job duration, voice-worker call counters và LLM analytics call counters.
- Các metrics này chỉ dành cho Prometheus trong mạng Docker; frontend không gọi trực tiếp worker `/metrics`.

---

## Quản lý cấu hình tập trung Master `.env`

Tất cả các file `.env` cục bộ nằm trong thư mục của từng Worker đã được di chuyển hoàn chỉnh ra tệp **Master [`.env`](file:///d:/voice-sentiment/.env) ở thư mục root**. 

Khi chạy docker compose, các tham số cấu hình ASR của `voice-worker` (như `VOICE_LANGUAGE_CODE`, `PYTHONUNBUFFERED`) và cấu hình nghiệp vụ của `llm-worker` (như `VOICE_SERVER_URI`, `LLM_BASE_URL`, `LLM_MODEL`) sẽ được nạp động từ tệp root này, giúp giữ cho các container luôn sạch sẽ và bảo mật tối ưu nhất khi đóng gói.
