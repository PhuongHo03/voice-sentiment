# Tài liệu giải thích Worker

## Mục đích

Thư mục `worker/` chịu trách nhiệm xử lý các tác vụ AI nặng (nhiệm vụ đòi hỏi nhiều tài nguyên tính toán) để giúp dịch vụ Backend luôn nhẹ nhàng và tối ưu. Worker tiêu thụ các công việc phân tích từ hàng đợi, chạy các mô hình AI âm thanh/văn bản, ghi kết quả bền vững vào cơ sở dữ liệu và cập nhật trạng thái bộ nhớ đệm cache.

## Cấu trúc thư mục

```text
worker/
├── app/main.py                         ← Điểm khởi chạy nhận tin nhắn RabbitMQ và cấu hình Logging
├── app/core/config.py                  ← Cấu hình môi trường cho Worker (voice_* và llm_*)
├── app/domain/analysis.py              ← Định nghĩa kiểu dữ liệu Domain của hội thoại/kết quả
├── app/application/use_cases/          ← Use case xử lý phân tích công việc
├── app/infrastructure/ai/              ← Các bộ điều hợp kết nối local Whisper ASR và LLM (OpenAI-compatible)
├── app/infrastructure/database/        ← Khởi tạo SQLAlchemy repository lưu kết quả/trạng thái
├── app/infrastructure/storage/         ← Bộ điều hợp tải tệp tin âm thanh từ MinIO
├── app/infrastructure/cache/           ← Bộ điều hợp cập nhật trạng thái công việc vào Redis
└── app/infrastructure/queue/           ← Bộ tiêu thụ hàng đợi RabbitMQ
```

## Quy trình xử lý công việc (Job flow)

1. Tiêu thụ (consume) tin nhắn từ hàng đợi `analysis.jobs` của RabbitMQ.
2. Đánh dấu công việc ở trạng thái `processing` trong cả PostgreSQL và Redis.
3. **Đối với công việc âm thanh**: tải tệp tin âm thanh từ MinIO và sử dụng mô hình **local CPU `faster-whisper`** (được cấu hình lượng tử hóa `int8` để tối ưu RAM) để chuyển đổi giọng nói thành văn bản tiếng Việt.
4. **Đối với công việc văn bản**: đóng gói nội dung văn bản đầu vào thành một lượt hội thoại của người nói.
5. Gửi văn bản hội thoại đến mô hình LLM qua API `/chat/completions` (tương thích OpenAI, ví dụ vLLM hoặc các dịch vụ khác) và yêu cầu định dạng đầu ra bắt buộc là JSON hợp lệ chứa tóm tắt (`summary`), sắc thái cảm xúc (`sentiment`), lý do đánh giá (`sentiment_reason`), và độ tự tin (`confidence`).
6. Lưu trữ đoạn hội thoại, danh sách tóm tắt, và phân tích sắc thái cảm xúc bền vững vào PostgreSQL.
7. Cập nhật cache trạng thái thành công (`completed`) hoặc thất bại (`failed`) vào Redis để API truy vấn nhanh.

*Lưu ý: Mô hình local Whisper hiện tại tự động gán nhãn người phát biểu mặc định là `Khách hàng`.*

## Chuẩn hóa âm thanh (Audio Normalization - FFmpeg)

Để hỗ trợ nhiều định dạng âm thanh khác nhau từ người dùng (như luồng WebM Opus ghi âm trực tiếp từ trình duyệt, `.mp3`, hoặc `.wav`), dịch vụ Worker tích hợp một bộ chuẩn hóa âm thanh sử dụng công cụ `ffmpeg` chạy dưới dạng tiến trình con (subprocess), đặt tại `app/infrastructure/storage/audio_normalizer.py`.
Bộ chuẩn hóa này sẽ tự động chuyển đổi mọi luồng âm thanh đầu vào thành định dạng **linear PCM, 16kHz, mono 16-bit WAV** trực tiếp thông qua luồng RAM (stdin/stdout pipes) mà không cần ghi file tạm ra ổ đĩa, đảm bảo khả năng tương thích tuyệt đối với mô hình local Whisper.

## Bộ điều hợp AI thực tế (Sử dụng 100% Real Mode - Không Mock)

Worker tương tác với các hệ thống AI thực tế thông qua các bộ điều hợp (adapters) sạch sẽ, không có bất kỳ cấu trúc mock giả lập nào:
1. **Local Whisper ASR (`whisper_stt_client.py`)**: Sử dụng thư viện `faster-whisper` để giải mã âm thanh cục bộ trên CPU. Mô hình `small` tiếng Việt tự động tải về khi chạy lần đầu và được cache trong thư mục `/root/.cache` của container để tái sử dụng ngay lập tức cho các lần chạy sau.
2. **LLM Analytics (`llm_client.py`)**: Gửi yêu cầu tóm tắt và đánh giá sắc thái cuộc gọi đến API tương thích với OpenAI (cấu hình qua địa chỉ `LLM_BASE_URL` như máy chủ vLLM, OpenAI, v.v.) và tiến hành dọn dẹp, phân tích chuỗi JSON đầu ra cực kỳ nghiêm ngặt.

## Cấu hình môi trường (Env)

File `worker/.env.example` định nghĩa cấu hình kết nối tới PostgreSQL, Redis, RabbitMQ, MinIO, Voice (Whisper), và LLM. Các biến cấu hình chính bao gồm:
- `VOICE_SERVER_URI=local`
- `VOICE_LANGUAGE_CODE=vi-VN`
- `LLM_BASE_URL=http://localhost:8001/v1`
- `LLM_MODEL=your-model-name`
- `PYTHONUNBUFFERED=1` (giúp đẩy log của Python ra màn hình Docker thời gian thực)

*Tài liệu phản ánh trạng thái worker sau khi hoàn thành loại bỏ mock và đổi tên biến.*
