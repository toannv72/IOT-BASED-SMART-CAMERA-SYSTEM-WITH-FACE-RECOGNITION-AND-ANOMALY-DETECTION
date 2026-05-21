# Hướng Dẫn Vận Hành Hệ Thống Giám Sát YOLO & FaceNet

Chào mừng bạn đến với hệ thống giám sát an ninh thông minh kết hợp giữa **YOLO** (Phát hiện đối tượng, theo dõi hành vi, đếm người, khoanh vùng xâm nhập ROI) và **FaceNet** (Trích xuất đặc trưng và nhận diện khuôn mặt).

Tài liệu này hướng dẫn chi tiết cách cài đặt môi trường và các lệnh để chạy từng thành phần của hệ thống.

---

## 🛠️ 1. Chuẩn Bị Môi Trường

Đầu tiên, bạn cần cài đặt các thư viện Python cần thiết. Chúng tôi đã chuẩn bị sẵn file [requirements.txt](file:///d:/CODE/yolo/requirements.txt).

Chạy lệnh sau trong Terminal (CMD / PowerShell / Bash):

```bash
pip install -r requirements.txt
```

---

## 🚀 2. Phân Hệ Nhận Diện Khuôn Mặt (FaceNet)

Phân hệ này hoạt động dựa trên mô hình Client-Server. Bạn **BẮT BUỘC** phải chạy API Server trước khi chạy các client nhận diện.

### Bước 2.1: Chạy API Server (Lưu trữ và trích xuất khuôn mặt)
Server sử dụng FastAPI để quản lý dữ liệu khuôn mặt và SQLite (`faces.db`) làm cơ sở dữ liệu.

* **Lệnh chạy:**
  ```bash
  python face_api.py
  ```
* **Địa chỉ hoạt động:** `http://localhost:8000`
* **API Documentation (Swagger UI):** Truy cập `http://localhost:8000/docs` trên trình duyệt để kiểm tra trực quan.

### Bước 2.2: Đăng ký khuôn mặt mới (Webcam)
Công cụ này sẽ mở camera của bạn, cho phép bạn chụp hình ảnh khuôn mặt và lưu tên vào cơ sở dữ liệu qua API.

* **Lệnh chạy:**
  ```bash
  python register_face.py
  ```
* **Cách sử dụng:**
  1. Đưa khuôn mặt vào khung màu xanh lá cây trên cửa sổ hiển thị.
  2. Nhấn phím **`s`** để chụp ảnh.
  3. Nhập tên của bạn ở cửa sổ dòng lệnh (Terminal/Console) và nhấn **Enter**.
  4. Nhấn **`q`** để thoát.

### Bước 2.3: Nhận diện khuôn mặt thời gian thực (Webcam)
Script này sẽ mở webcam, phát hiện các khuôn mặt hiện có và gửi đặc trưng để so khớp với dữ liệu đã đăng ký trên API.

* **Lệnh chạy:**
  ```bash
  python face_camera.py
  ```
* **Phím tắt:**
  * Nhấn **`r`** để tải lại (reload) danh sách khuôn mặt mới từ database (không cần khởi động lại script).
  * Nhấn **`q`** để thoát.

### Bước 2.4: Nhận diện khuôn mặt từ file ảnh tĩnh
Sử dụng hình ảnh có sẵn trong máy để nhận diện khuôn mặt.

* **Lệnh chạy mặc định** (Sử dụng file ảnh mặc định `test.jpg`):
  ```bash
  python recognize_image.py
  ```
* **Lệnh chạy với file ảnh tùy chọn:**
  ```bash
  python recognize_image.py path/to/your/image.jpg
  ```

---

## 📈 3. Phân Hệ Giám Sát Xâm Nhập & Đếm Người (YOLO)

Phân hệ này sử dụng mô hình YOLOv5 hoặc YOLOv8 để phát hiện con người và thực hiện các phân tích hành vi nâng cao.

### 3.1. Đếm người qua vạch kẻ (Đa camera - YOLOv8)
Sử dụng đa luồng (multi-threading) để xử lý nhiều camera đồng thời, đếm số người đi qua vạch (IN / OUT) và tính tổng số người hiện tại.

* **Cấu hình camera:** File [cameras_config.json](file:///d:/CODE/yolo/cameras_config.json)
* **Lệnh chạy:**
  ```bash
  python multi_cam_counter.py
  ```
* **Phím tắt:** Nhấn **`q`** để tắt hệ thống.

### 3.2. Giám sát xâm nhập vùng ROI trên Video (YOLOv5)
Khoanh vùng khu vực cần bảo vệ (ROI - Region of Interest). Khi có người đi vào vùng này, hệ thống sẽ kích hoạt cảnh báo đỏ và gửi ảnh kèm tin nhắn cảnh báo qua Telegram.

* **Lệnh chạy:**
  ```bash
  python test_video.py
  ```
* **Cách thao tác:**
  * **Vẽ vùng ROI:** Click chuột trái lên màn hình video để chấm các điểm tạo thành đa giác bảo vệ.
  * **Xóa vùng ROI:** Click chuột phải lên màn hình video để xóa vùng vẽ lại từ đầu.
  * **Thoát:** Nhấn **`q`**.

### 3.3. Xử lý hàng loạt video sự kiện (YOLOv5)
Quét thư mục chứa các video đầu vào, vẽ vùng ROI cho từng video. Nếu phát hiện xâm nhập, hệ thống sẽ trích xuất đoạn video chứa sự kiện đó (gồm 1 phút trước sự kiện lưu trong bộ đệm và 1 phút sau khi sự kiện kết thúc) để lưu lại, đồng thời gửi cảnh báo Telegram.

* **Thư mục đầu vào:** `input_videos/`
* **Thư mục lưu sự kiện:** `output_events/`
* **Lệnh chạy:**
  ```bash
  python video_event_handler.py
  ```

---

## 💻 4. Tích Hợp Trên Thiết Bị Biên (Edge Device)

Thư mục `edge_device/` chứa các script tối ưu riêng cho việc chạy trên các thiết bị biên (Jetson Nano, Raspberry Pi, Máy tính trạm tại chỗ).

### 4.1. Khởi chạy Edge Node tích hợp (YOLOv8 + FaceNet + Telegram Alert)
Edge Node sẽ thực hiện đồng thời:
1. Quét người bằng YOLOv8.
2. Trích xuất khuôn mặt bằng FaceNet.
3. Nếu là khuôn mặt đã đăng ký trên API -> Hiển thị tên (màu xanh lá).
4. Nếu phát hiện người lạ (Unknown) -> Đổi màu đỏ và lập tức gửi hình ảnh cảnh báo đột nhập tới Telegram của các admin quản trị.

* **Lệnh chạy:**
  ```bash
  python edge_device/main_edge_node.py
  ```

### 4.2. Đăng ký khuôn mặt từ Edge Device
* **Lệnh chạy:**
  ```bash
  python edge_device/register_face.py
  ```

---

## 📲 5. Cấu Hình Cảnh Báo Telegram

Để nhận được tin nhắn cảnh báo trực tiếp về điện thoại của bạn qua Telegram:
1. Mở các file: `test_video.py`, `video_event_handler.py`, hoặc `edge_device/main_edge_node.py`.
2. Tìm biến `TELEGRAM_TOKEN` và thay bằng Token Bot Telegram của bạn (Tạo qua `@BotFather`).
3. Tìm biến `TELEGRAM_CHAT_IDS` hoặc `TELEGRAM_CHAT_ID` và điền ID tài khoản của bạn (Lấy qua `@userinfobot`).

---

## 🖱️ 6. Chạy Bằng Menu Điều Khiển (Khuyên Dùng Trên Windows)

Nếu bạn sử dụng hệ điều hành Windows, hãy sử dụng công cụ menu được đóng gói sẵn để chạy nhanh chóng mà không cần gõ lệnh:

1. Click đúp chuột vào file **`chay_he_thong.bat`** ở thư mục gốc.
2. Gõ số tương ứng với tác vụ bạn muốn chạy (Ví dụ: `1` để cài đặt thư viện, `2` để chạy server, `3` để đăng ký khuôn mặt,...) và nhấn **Enter**.

---
*Chúc bạn chạy thử nghiệm thành công! Nếu gặp bất kỳ vấn đề gì về kết nối camera hoặc lỗi thư viện, hãy liên hệ hỗ trợ.*
