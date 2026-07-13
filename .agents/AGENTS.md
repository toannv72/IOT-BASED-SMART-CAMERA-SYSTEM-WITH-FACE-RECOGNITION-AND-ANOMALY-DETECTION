# TỔNG QUAN HỆ THỐNG & QUY ĐỊNH PHÁT TRIỂN DỰ ÁN SMART CAMERA

Tài liệu này chứa thông tin tổng quan về kiến trúc kỹ thuật và các quy định bắt buộc đối với tất cả các Trợ lý AI khi làm việc trên dự án này. AI phải đọc và tuân thủ nghiêm ngặt các quy định dưới đây để tránh phá vỡ mã nguồn đã được tối ưu hóa và biên dịch thành công.

---

## I. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Dự án này là hệ thống **Smart Camera giám sát đa nguy cơ biên** (Edge AI), được thiết kế để chạy thực tế trên thiết bị phần cứng **Raspberry Pi 4 Model B (8GB RAM)** (CPU Mode) kết nối với Webcam USB, tích hợp cảm biến khí ga MQ-2 và rơ-le khóa cửa điện từ Solenoid.

### 1. Phân hệ Thị giác Máy tính & AI (Edge-CPU)
* **Khóa Luồng Đồng Bộ (Concurrency Lock)**:
  * Do Raspberry Pi 4 không có GPU rời, toàn bộ mô hình AI được chạy trên CPU.
  * Tắt chế độ tính toán gradient bằng `with torch.no_grad():` để tiết kiệm bộ nhớ RAM.
  * Sử dụng khóa lock toàn cục `gpu_lock = threading.Lock()` tại tệp `app/processors.py` để đồng bộ hóa tuần tự suy luận giữa các luồng camera, tránh gây nghẽn và tràn bộ nhớ CPU biên.
* **Nhận diện khuôn mặt đeo khẩu trang (Masked Face Recognition)**:
  * Hệ thống sử dụng cặp mô hình **MTCNN** (phát hiện khuôn mặt) + **FaceNet** (trích xuất đặc trưng L2-Norm 512 chiều).
  * Hỗ trợ nhận diện người đeo khẩu trang chỉ với **1 ảnh mẫu không đeo khẩu trang** bằng cách bôi đen (zero out) 45% phần dưới khuôn mặt kích thước `160x160` (vùng mũi xuống cằm):
    * Ảnh đăng ký: `face[:, 88:, :] = 0.0` (tại `app/routes.py`).
    * Khung hình stream: `faces[:, :, 88:, :] = 0.0` (tại `app/processors.py`).
  * Ngưỡng so khớp L2-Norm tối ưu được đặt cố định ở giá trị **`0.80`** (tại `app/config.py`).

### 2. Phân hệ Cảm biến Khí ga MQ-2 (Gas Leak Alert)
* **Chân cắm GPIO**: Digital Output (DO) của cảm biến MQ-2 nối vào **GPIO 18 (Pin 12)** trên Pi 4.
* **Cơ chế hoạt động**: Chạy vòng lặp kiểm tra trạng thái GPIO mỗi giây. Nếu phát hiện rò rỉ (mức LOW từ chân DO), hệ thống sẽ:
  * Kích hoạt cờ trạng thái `SystemStatus.gas_active = True`.
  * Ghi nhật ký vào SQLite database.
  * Gửi tin nhắn khẩn cấp qua Telegram Bot (áp dụng cooldown 30 giây tránh spam).

### 3. Phân hệ Khóa cửa điện từ (Solenoid Door Lock Relay)
* **Chân cắm GPIO**: Chân tín hiệu Rơ-le (Relay) nối vào **GPIO 23 (Pin 16)** trên Pi 4.
* **Cơ chế hoạt động**: Khi nhận lệnh mở cửa, hệ thống sẽ:
  * Đặt cờ `SystemStatus.door_unlock_active = True`.
  * Xuất mức HIGH ra GPIO 23 trong vòng **3 giây** (hút rơ-le thông mạch cấp nguồn mở khóa), sau đó trả về mức LOW (khóa chốt) để tránh cháy cuộn hút.
  * Đặt lại cờ `SystemStatus.door_unlock_active = False`.

### 4. Giao tiếp 2 chiều với Telegram Bot (Long Polling)
* Bot tự động xóa Webhook và chạy cơ chế Long Polling qua luồng daemon trong tệp `app/alerts.py`.
* Hỗ trợ các nút tương tác Inline: Tắt báo động (`mute_alerts`), tạm dừng camera (`pause_<cam_id>_30`), mở cửa từ xa (`unlock_door`).
* Hỗ trợ xử lý tin nhắn lệnh trực tiếp từ Admin: Nhận diện `/unlock`, `/mo_cua`, `unlock`, `mo cua`, `mở cửa` để gọi hàm mở cửa.

---

## II. QUY ĐỊNH PHÁT TRIỂN & BẢO TRÌ MÃ NGUỒN (AI CONSTRAINTS)

Để bảo vệ dự án khỏi các lỗi tương thích phần cứng và giữ vững tính ổn định, mọi hành vi sửa đổi mã nguồn của AI phải tuân thủ nghiêm ngặt các quy định sau:

### 1. Không thay đổi giải pháp Nhận diện Khẩu trang & Ngưỡng so khớp
* **NGHIÊM CẤM** gỡ bỏ hoặc thay đổi công thức bôi đen 45% phần mặt dưới: `[:, 88:, :] = 0.0`. Đây là giải pháp cốt lõi để nhận dạng người đeo khẩu trang chỉ với 1 ảnh mẫu gốc không khẩu trang mà không cần huấn luyện lại mô hình deep learning.
* **NGHIÊM CẤM** giảm ngưỡng `"face_threshold"` xuống dưới `0.78` hoặc tăng vượt quá `0.82` (mặc định là `0.80`).

### 2. Đảm bảo tính Cross-Platform (Chạy được trên cả Laptop phát triển và Raspberry Pi biên)
* Raspberry Pi 4 sử dụng thư viện `RPi.GPIO` để đọc ghi các chân GPIO vật lý. Tuy nhiên, thư viện này **không khả dụng trên Windows/macOS** của máy tính phát triển.
* Do đó, mọi mã nguồn GPIO phải được bao bọc trong khối lệnh thử nghiệm an toàn:
  ```python
  try:
      import RPi.GPIO as GPIO
      has_gpio = True
  except ImportError:
      has_gpio = False
  ```
* Nếu `has_gpio` là `False`, hệ thống phải tự động chuyển sang chế độ **giả lập** (ví dụ: đọc trạng thái giả lập qua biến `SystemStatus.mock_gas_leak` hoặc giả lập log console khi mở cửa) thay vì báo lỗi crash hệ thống.

### 3. Giữ nguyên cấu trúc đồng bộ đa luồng
* **NGHIÊM CẤM** gỡ bỏ khóa `gpu_lock` trong các hàm xử lý mô hình AI. Việc chạy các mô hình AI song song không đồng bộ trên CPU của Raspberry Pi 4 chắc chắn sẽ dẫn đến quá tải luồng, rò rỉ bộ nhớ, treo cứng hệ thống hoặc crash tiến trình.
* Luôn bọc các câu lệnh chạy mô hình trong khối:
  ```python
  with gpu_lock:
      with torch.no_grad():
          # thực hiện suy luận mô hình ở đây
  ```

### 4. Quy định bảo vệ mã nguồn thuyết minh (LaTeX)
* Các tệp thuyết minh luận văn tốt nghiệp nằm tại `de_tai_thac_si.tex` (bản tiếng Anh) và `de_tai_thac_si_vi.tex` (bản tiếng Việt).
* Khi cập nhật mô hình triển khai phần cứng, luôn phải giữ nhãn thiết bị biên là **`Raspberry Pi 4`** thay vì các thiết bị máy trạm GPU RTX khác.
* Sau khi chỉnh sửa tệp `.tex`, phải chạy lệnh biên dịch hai lượt (`pdflatex <filename>.tex`) để đồng bộ hoàn toàn mục lục và tham chiếu chéo trong tệp PDF tương ứng.

### 5. Đóng gói & Bàn giao sản phẩm
* Sau khi thực hiện bất kỳ thay đổi nào liên quan đến mã nguồn, tài liệu hướng dẫn cắm dây, hoặc thuyết minh luận văn, AI bắt buộc phải chạy lại script đóng gói tự động:
  ```bash
  python don_dep_dong_goi.py
  ```
  để dọn dẹp bộ nhớ đệm rác và nén toàn bộ mã nguồn sạch cùng các tệp PDF báo cáo mới nhất vào tệp nén **`SmartCamera_System.zip`** nằm ngoài thư mục cha của dự án.
