# Tài liệu giải thích Frontend

## Mục đích

Thư mục `frontend/` chứa bảng điều khiển quản trị (Dashboard) viết bằng React + Vite + TypeScript dùng để tải lên tệp tin hoặc ghi âm trực tiếp các cuộc gọi, từ đó hiển thị các kết quả phân tích sắc thái cảm xúc và tóm tắt cuộc hội thoại một cách trực quan.

## Cấu trúc thư mục

```text
frontend/
├── src/app/App.tsx                     ← Khung xương bọc ngoài ứng dụng (App shell)
├── src/pages/DashboardPage.tsx         ← Bố cục trang Dashboard chính
├── src/components/audio/               ← Các thành phần tải file, ghi âm, và ô nhập text test nhanh
├── src/components/transcript/          ← Thành phần hiển thị nội dung hội thoại chia theo vai nói
├── src/components/summary/             ← Thẻ hiển thị các bullet point tóm tắt cuộc gọi
├── src/components/sentiment/           ← Huy hiệu hiển thị sắc thái cảm xúc (Sentiment badge)
├── src/hooks/                          ← Các hooks quản lý ghi âm và truy vấn lặp trạng thái phân tích
├── src/services/analysisApi.ts         ← Client kết nối gọi API Backend
└── src/types/analysis.ts               ← Định nghĩa các kiểu dữ liệu dùng chung trên giao diện
```

## Luồng xử lý giao diện (UI flow)

1. Giao diện Dashboard gửi tệp tin âm thanh hoặc văn bản kiểm thử lên Backend, nhận lại mã định danh `job_id`.
2. Giao diện tự động thực hiện cơ chế truy vấn lặp liên tục (`GET /api/analysis/{job_id}`) để theo dõi tiến độ xử lý của Worker.
3. Khi Worker xử lý xong (`completed`), giao diện sẽ ngay lập tức render các lượt hội thoại sinh động phân chia theo người nói (Transcript turns), các ý tóm tắt cuộc gọi sắc bén (Summary bullets), và huy hiệu sắc thái cảm xúc kèm điểm tự tin tương ứng.
4. Trình duyệt thực hiện ghi âm trực tiếp từ microphone bằng API `MediaRecorder`. Tệp tin ghi âm đầu ra thường có định dạng `audio/webm` (sử dụng codec Opus). Nhờ có cơ chế chuẩn hóa âm thanh tự động bằng FFmpeg ở phía Worker vừa được hoàn thiện tại **Giai đoạn 2**, các tệp tin ghi âm `.webm` này giờ đây đã được chuyển đổi hoàn hảo và dịch thành công mà không gặp bất kỳ trở ngại nào.

## Cấu hình môi trường (Env)

File `frontend/.env.example` định nghĩa biến `VITE_API_BASE_URL` trỏ tới địa chỉ API Backend (khi chạy local, chúng ta định tuyến qua proxy Nginx ở địa chỉ `http://localhost:8082` để tránh hoàn toàn lỗi CORS).

*Tài liệu phản ánh trạng thái frontend tại giai đoạn hoàn thành Giai đoạn 2.*
