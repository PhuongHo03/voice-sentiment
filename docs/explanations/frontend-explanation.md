# Tài liệu giải thích Frontend

## Mục đích

Thư mục `frontend/` chứa bảng điều khiển quản trị (Dashboard) viết bằng React + Vite + TypeScript. Giao diện cho phép người dùng tải lên tệp tin hoặc ghi âm trực tiếp các cuộc gọi thoại, quản lý lịch sử phiên phân tích, xem kết quả sắc thái cảm xúc, đánh giá hiệu suất nhân viên, và theo dõi xu hướng thống kê tổng hợp qua Dashboard.

---

## Cấu trúc thư mục

```text
frontend/
├── src/app/App.tsx                     ← Khung xương bọc ngoài ứng dụng (App shell)
├── src/pages/DashboardPage.tsx         ← Trang Dashboard chính: quản lý session, biểu đồ thống kê, scorecard nhân viên
├── src/components/audio/               ← Các thành phần tải file, ghi âm, và ô nhập text phân tích nhanh
├── src/components/transcript/          ← Thành phần hiển thị nội dung hội thoại chia theo vai nói sinh động
├── src/components/summary/             ← Thẻ hiển thị các bullet point tóm tắt cuộc gọi sắc bén
├── src/components/sentiment/           ← Huy hiệu hiển thị sắc thái cảm xúc tổng thể (Sentiment badge)
├── src/hooks/                          ← Các hooks quản lý luồng ghi âm và truy vấn lặp trạng thái phân tích
├── src/services/analysisApi.ts         ← Client kết nối gọi các API phân tích của Backend
├── src/styles/main.css                 ← Design system tokens, glassmorphism, dashboard & agent scorecard styles
└── src/types/analysis.ts               ← Định nghĩa các kiểu dữ liệu dùng chung trên giao diện
```

---

## Luồng xử lý giao diện (UI Flow)

### Chế độ Phân tích Phiên (`activeView = 'session'`)

1.  **Quản lý Sidebar Phiên**: Giao diện hiển thị danh sách lịch sử phiên phân tích (tải qua `GET /api/analysis`). Người dùng có thể:
    *   Nhấn vào phiên để xem chi tiết kết quả.
    *   **Tìm kiếm** phiên theo từ khoá trong thanh tìm kiếm sidebar.
    *   **Đổi tên** phiên bằng cách nhấn đúp (inline rename → `PATCH /api/analysis/{id}`).
    *   **Xoá** phiên (kéo theo xoá file MinIO + cache Redis → `DELETE /api/analysis/{id}`).
2.  **Gửi Yêu Cầu Mới**: Panel chính cho phép người dùng nhập văn bản kiểm thử nhanh hoặc ghi âm/tải lên tệp âm thanh. Sau khi nhấn phân tích, giao diện gửi dữ liệu lên Backend và nhận lại mã định danh duy nhất `job_id`. Phiên mới tự động xuất hiện ở đầu danh sách sidebar.
3.  **Truy Vấn Lặp (Polling)**: Giao diện tự động thực hiện cơ chế truy vấn lặp liên tục (`GET /api/analysis/{job_id}`) mỗi 2 giây để theo dõi tiến độ xử lý của hệ thống.
4.  **Hiển Thị Kết Quả Hoàn Thành**: Khi trạng thái chuyển sang `completed`, giao diện sẽ lập tức hiển thị:
    *   Các lượt hội thoại chia vai nói kèm thời gian chi tiết (Transcript turns).
    *   Các điểm tóm tắt cuộc hội thoại thông minh (Summary bullets).
    *   Huy hiệu cảm xúc động (Tích cực, Tiêu cực, Trung lập) kèm điểm số tự tin tương ứng.
    *   **Thẻ Đánh Giá Nhân Viên**: Hiển thị điểm tròn động (`agent_score` / 10), nhãn xếp loại (Xuất sắc / Tốt / Cần cải thiện), và danh sách lời khuyên hành động từ LLM (`agent_advice`).
5.  **Ghi Âm Microphone Trực Tiếp**: Trình duyệt sử dụng API `MediaRecorder` để thu âm trực tiếp từ microphone của người dùng. Tệp âm thanh đầu ra có định dạng `audio/webm` (sử dụng codec Opus). Nhờ có cơ chế tự động chuyển đổi định dạng âm thanh bằng FFmpeg bên trong dịch vụ `voice-worker`, các tệp tin `.webm` này được giải mã và nhận diện ngôn ngữ tiếng Việt thành công mà không gặp bất kỳ trở ngại nào.

### Chế độ Dashboard Thống Kê (`activeView = 'dashboard'`)

Người dùng nhấn nút **"Phân tích cuộc gọi"** trên sidebar để chuyển sang chế độ Dashboard. Dữ liệu được tải từ `GET /api/analysis/stats` và hiển thị:

*   **Thẻ số liệu tổng quan**: Tổng số phân tích, điểm nhân viên trung bình, tỉ lệ tích cực.
*   **Biểu đồ vòng (SVG Donut Chart)**: Phân phối tỉ lệ sentiment (Tích cực / Trung lập / Tiêu cực) theo phần trăm.
*   **Biểu đồ cột (Bar Chart)**: Phân phối điểm nhân viên theo các khoảng điểm (0-3, 4-6, 7-8, 9-10).
*   **Xu hướng 7 ngày (Weekly Trend)**: Số lượng phân tích mỗi ngày trong 7 ngày gần nhất.

---

## Trạng Thái & Navigation UI

```
activeView = 'session'           ← Xem/tạo phiên phân tích đơn lẻ
activeView = 'dashboard'         ← Xem tổng hợp thống kê
```

Cả hai chế độ chia sẻ cùng layout sidebar (có thể thu gọn) và đầu trang thương hiệu.

---

## Kiểu Dữ Liệu Chính (Types)

Định nghĩa trong `src/types/analysis.ts`:

```typescript
interface TranscriptTurn {
  speaker: string;
  text: string;
  start_seconds: number | null;
  end_seconds: number | null;
}

interface AnalysisResult {
  transcript: TranscriptTurn[];
  summary: string[];
  sentiment: 'positive' | 'neutral' | 'negative' | string;
  sentiment_reason: string;
  confidence: number;
  agent_score?: number | null;      // Điểm đánh giá nhân viên 0-10
  agent_advice?: string[] | null;   // Lời khuyên hành động từ LLM
}

interface JobStatus {
  job_id: string;
  name: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  input_type: 'audio' | 'text';
  result: AnalysisResult | null;
  error_message: string | null;
}

interface SessionListItem {
  job_id: string;
  name: string | null;
  status: string;
  input_type: string;
  created_at: string;
  sentiment: string | null;
  confidence: number | null;
}
```

---

## Cấu Mạng & Cổng Giao Tiếp (Network Configuration)

*   **File `.env` và `.env.example`**: Định nghĩa biến cấu hình `VITE_API_BASE_URL` trỏ tới địa chỉ Gateway.
*   **Proxy Nginx (`9090`)**: Khi chạy thực tế trên host, toàn bộ tài nguyên frontend (static assets) và yêu cầu API (`/api/*`, `/health`) đều được định tuyến thông qua Proxy ngược **Nginx** ở địa chỉ **`http://localhost:9090`**. Thiết lập này giúp giải quyết triệt để lỗi chia sẻ tài nguyên nguồn gốc chéo (CORS) trên trình duyệt mà không cần mở các cổng bảo mật phụ.

> [!NOTE]
> **Container Port Security**: Tương tự như backend, cổng máy chủ chạy thử nghiệm Vite (`5173`) được ẩn hoàn toàn khỏi mạng host bên ngoài. Nginx đóng vai trò là điểm chạm duy nhất trên host ở cổng `9090` để phục vụ ứng dụng Frontend và chuyển tiếp API đến Backend một cách an toàn.
