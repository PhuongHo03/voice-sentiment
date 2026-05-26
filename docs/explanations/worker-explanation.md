# Tài liệu giải thích hệ thống Worker (Decoupled Microservices)

## Mục đích

Để tối ưu hóa hiệu năng, tăng khả năng mở rộng (scale) và nâng cao tính tái sử dụng, hệ thống xử lý nền (background worker) của dự án đã được phân tách hoàn chỉnh thành hai dịch vụ microservices độc lập:

1.  **`voice-worker` (Stateless ASR Web Server)**: Dịch vụ FastAPI thuần túy nhận nhiệm vụ chuyển đổi giọng nói thành văn bản (Speech-to-Text) bằng mô hình `faster-whisper` chạy cục bộ trên CPU.
2.  **`llm-worker` (RabbitMQ Orchestrator)**: Dịch vụ tiêu thụ tin nhắn từ hàng đợi RabbitMQ, điều phối quy trình tải file từ MinIO, gọi dịch vụ `voice-worker` để lấy văn bản hội thoại, gọi mô hình LLM tương thích OpenAI từ xa để phân tích sắc thái cảm xúc và đánh giá hiệu suất nhân viên, và lưu trữ kết quả vào PostgreSQL và Redis cache.

---

## Cấu trúc thư mục

```text
├── voice-worker/
│   ├── app/main.py                         ← Điểm khởi chạy FastAPI exposes cổng 8000 (Host: 9095)
│   ├── app/core/config.py                  ← Cấu hình môi trường riêng cho ASR (mô hình, ngôn ngữ)
│   ├── app/infrastructure/ai/              ← Bộ điều hợp gọi cục bộ faster-whisper STT
│   │   └── whisper_stt_client.py           ← FFmpeg audio normalization + faster-whisper inference
│   ├── Dockerfile                          ← Cài đặt Python, FFmpeg, và các thư viện ASR
│   ├── requirements.txt                    ← Thư viện hỗ trợ: fastapi, faster-whisper, httpx, uvicorn
│   └── .env                                ← File cấu hình cục bộ cho voice-worker
│
├── llm-worker/
│   ├── app/main.py                         ← Điểm chạy nền lắng nghe RabbitMQ và khởi tạo logs
│   ├── app/core/config.py                  ← Cấu hình kết nối tới DB, Cache, Queue, LLM và voice-worker
│   ├── app/domain/analysis.py              ← Định nghĩa thực thể Domain hội thoại và kết quả phân tích
│   ├── app/application/use_cases/
│   │   └── analyze_job.py                  ← Use case điều phối: audio/text → STT → LLM → DB/Cache
│   ├── app/infrastructure/ai/
│   │   └── llm_client.py                   ← Client gọi LLM bên ngoài, trả về sentiment + agent evaluation
│   ├── app/infrastructure/database/        ← SQLAlchemy repository lưu kết quả bền vững vào Postgres
│   ├── app/infrastructure/storage/         ← S3 Client tải file âm thanh nguồn từ MinIO
│   ├── app/infrastructure/cache/           ← Redis Client cập nhật bộ nhớ đệm cache trạng thái công việc
│   ├── app/infrastructure/queue/           ← RabbitMQ consumer lắng nghe hàng đợi 'analysis.jobs'
│   ├── Dockerfile                          ← Image siêu nhẹ chứa thư viện Python (không cần FFmpeg/Whisper)
│   ├── requirements.txt                    ← Thư viện hỗ trợ: pika, sqlalchemy, redis, minio, httpx
│   └── .env                                ← File cấu hình cục bộ cho llm-worker
```

---

## Phân tích Chi tiết Từng Dịch Vụ

### 1. `voice-worker` (Stateless ASR)
*   **Thiết kế Stateless**: Hoàn toàn không kết nối tới cơ sở dữ liệu Postgres, bộ nhớ đệm Redis hay hàng đợi RabbitMQ. Dịch vụ hoạt động như một máy chủ API độc lập trong mạng LAN.
*   **API Đầu Vào**: Cung cấp API `POST /api/transcribe` nhận tệp âm thanh dạng multipart form-data.
*   **Whisper STT (`whisper_stt_client.py`)**: Sử dụng thư viện `faster-whisper` tối ưu hóa cao chạy trên CPU. Khi chạy lần đầu, mô hình `small` được tự động tải từ Hugging Face xuống bộ nhớ cache `/root/.cache` của container để tái sử dụng ngay lập tức trong các lần tiếp theo.
*   **Ngôn ngữ**: Mặc định cấu hình tự động nhận diện ngôn ngữ (`auto`) để hỗ trợ chuyển dịch đa ngôn ngữ một cách linh hoạt nhất.
*   **Timeout**: `llm-worker` gọi `voice-worker` với timeout `httpx.Client(timeout=1800)` — 30 phút. Nếu `voice-worker` chưa tải xong mô hình hoặc container bị tắt, sẽ xảy ra lỗi `Voice-worker STT service connection failed: timed out`. Khắc phục: kiểm tra `docker compose logs voice-worker` để đảm bảo container đã sẵn sàng.

### 2. `llm-worker` (RabbitMQ Orchestrator)
*   **Quy trình Xử lý Công việc (Job Flow)** trong `analyze_job.py`:
    1.  Tiêu thụ tin nhắn phân tích từ hàng đợi `analysis.jobs` trên RabbitMQ.
    2.  Đánh dấu trạng thái công việc là `processing` trong PostgreSQL và Redis.
    3.  **Nếu là Job âm thanh**:
        *   Tải file âm thanh tương ứng từ MinIO bucket `uploads`.
        *   Gửi file âm thanh qua HTTP POST request tới `voice-worker` tại địa chỉ nội bộ `http://voice-worker:8000/api/transcribe`.
        *   Nhận về danh sách các phân đoạn hội thoại (segments) kèm mốc thời gian (start/end seconds).
    4.  **Nếu là Job văn bản**: Bỏ qua bước STT, sử dụng trực tiếp nội dung văn bản truyền xuống.
    5.  Gửi dữ liệu cuộc hội thoại đến mô hình LLM tương thích OpenAI qua địa chỉ `LLM_BASE_URL` bằng client `llm_client.py` với cấu trúc prompt nghiêm ngặt bắt buộc trả về JSON.
    6.  Nhận về JSON kết quả gồm: tóm tắt cuộc gọi (`summary`), sắc thái cảm xúc tổng quan (`sentiment`), lý do đánh giá (`sentiment_reason`), điểm tự tin (`confidence`), **điểm nhân viên** (`agent_score` 0–10), và **lời khuyên nhân viên** (`agent_advice` danh sách hành động).
    7.  Lưu kết quả bền vững vào PostgreSQL (bao gồm `agent_score` và `agent_advice_json`) và cập nhật trạng thái `completed` trong bộ nhớ đệm Redis cache.
    8.  Gửi tín hiệu xác nhận (Acknowledge) hoàn thành tin nhắn lên RabbitMQ.

---

## Cấu trúc JSON Kết Quả LLM

LLM được yêu cầu trả về JSON có cấu trúc sau (bắt buộc qua prompt engineering):

```json
{
  "summary": ["Bullet điểm 1", "Bullet điểm 2"],
  "sentiment": "positive | neutral | negative",
  "sentiment_reason": "Lý do đánh giá sắc thái",
  "confidence": 0.92,
  "agent_score": 8,
  "agent_advice": [
    "Lời khuyên hành động 1 cho nhân viên",
    "Lời khuyên hành động 2 cho nhân viên"
  ]
}
```

`agent_score` phản ánh chất lượng phục vụ của nhân viên (0 = rất kém, 10 = xuất sắc).  
`agent_advice` là danh sách các gợi ý cụ thể để nhân viên cải thiện trong lần tương tác tiếp theo.

---

## Chuẩn hóa Âm thanh (Audio Normalization)

Quy trình chuẩn hóa âm thanh nằm tại `voice-worker` sử dụng công cụ `ffmpeg` chạy dưới dạng tiến trình con (subprocess), đặt tại `voice-worker/app/infrastructure/ai/whisper_stt_client.py`.
Mọi tệp tin âm thanh ghi âm từ trình duyệt (định dạng WebM Opus) hoặc các file nhạc (MP3, WAV) sẽ được tự động chuyển đổi thông qua RAM pipe thành định dạng chuẩn **Linear PCM, 1 Mono channel, 16kHz, 16-bit WAV**, đảm bảo tỷ lệ nhận dạng của Whisper đạt mức chính xác nhất mà không cần lưu trữ file tạm xuống đĩa cứng.

---

## Xử Lý Lỗi & Độ Bền Bỉ (Error Handling)

| Tình huống | Hành động |
|---|---|
| `voice-worker` không phản hồi (timeout) | Log lỗi, đánh dấu Job `failed`, lưu `error_message` vào DB |
| LLM không trả về JSON hợp lệ | Bắt exception, đánh dấu Job `failed` |
| MinIO file không tìm thấy | Exception → Job `failed` |
| Kết nối RabbitMQ bị ngắt | `pika` tự động reconnect theo cấu hình |
| Job thất bại | Redis cache được cập nhật `status: failed`, UI hiển thị thông báo lỗi |

---

## Biến Môi trường Tương ứng

*   **`voice-worker/.env`**:
    ```ini
    VOICE_MODEL_SIZE=small
    VOICE_COMPUTE_TYPE=int8
    VOICE_DEVICE=cpu
    ```
*   **`llm-worker/.env`**:
    ```ini
    # Database, Cache and Queue
    DATABASE_URL=postgresql://postgres:postgres@postgres:5432/voice_sentiment
    REDIS_URL=redis://redis:6379/0
    RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    
    # Storage (MinIO)
    MINIO_ENDPOINT=minio:9000
    MINIO_ACCESS_KEY=minioadmin
    MINIO_SECRET_KEY=minioadmin
    MINIO_BUCKET_NAME=uploads
    
    # STT Service API
    VOICE_SERVER_URI=http://voice-worker:8000
    
    # LLM Service API
    LLM_BASE_URL=http://192.168.2.74:8007/v1
    LLM_API_KEY=
    LLM_MODEL=google/gemma-4-E4B-it
    ```

---

## Giám Sát & Debug

```powershell
# Xem log thời gian thực của cả hai worker
docker compose logs -f voice-worker llm-worker

# Kiểm tra voice-worker đã sẵn sàng chưa (mô hình Whisper đã tải chưa)
docker compose logs voice-worker | Select-String "Uvicorn running"

# Kiểm tra trạng thái hàng đợi RabbitMQ
# Truy cập: http://localhost:9094 (guest/guest)
# Xem queue 'analysis.jobs' → Messages ready / Unacked / Total

# Xem lại kết quả phân tích trong DB
docker exec -it voice-sentiment-postgres-1 psql -U postgres -d voice_sentiment -c "SELECT id, status, error_message FROM analysis_jobs ORDER BY created_at DESC LIMIT 5;"
```
