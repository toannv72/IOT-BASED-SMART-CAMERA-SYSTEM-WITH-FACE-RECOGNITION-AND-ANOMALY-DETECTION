# HƯỚNG DẪN TRIỂN KHAI HỆ THỐNG TRÊN THIẾT BỊ BIÊN (EDGE/IoT)

Tài liệu này hướng dẫn chi tiết cách thiết lập và chạy mã nguồn hệ thống Camera thông minh giám sát đa tác vụ trực tiếp trên các thiết bị biên (Edge) thực tế như **Raspberry Pi 4/5** hoặc **NVIDIA Jetson Nano/Orin**, đáp ứng đúng mô hình kiến trúc Edge-Cloud IoT trong thực tế thuyết minh luận văn.

---

## 1. Yêu cầu Phần cứng & Hệ điều hành biên

### Lựa chọn 1: Raspberry Pi 4 (8GB) hoặc Raspberry Pi 5
* **Ưu điểm**: Giá rẻ, tiết kiệm điện, dễ thiết lập.
* **Hệ điều hành khuyên dùng**: Raspberry Pi OS (64-bit) hoặc Ubuntu Server 22.04 LTS (64-bit).
* **Đặc tính suy luận**: Sử dụng CPU biên thông qua thư viện PyTorch (CPU mode). Với khóa đồng bộ luồng `gpu_lock` và cơ chế suy luận tuần tự tránh race condition đã được cấu hình trong mã nguồn, hệ thống sẽ chạy cực kỳ ổn định.

### Lựa chọn 2: NVIDIA Jetson Nano / Jetson Orin Nano
* **Ưu điểm**: Tích hợp nhân đồ họa CUDA Cores, tăng tốc độ suy luận học sâu lên gấp 5-10 lần.
* **Hệ điều hành khuyên dùng**: NVIDIA JetPack SDK (Ubuntu-based).
* **Đặc tính suy luận**: Tận dụng tối đa tăng tốc phần cứng CUDA của GPU dùng chung.

---

## 2. Các bước triển khai chi tiết

### Bước 1: Đồng bộ mã nguồn lên thiết bị biên
Sử dụng Git hoặc sao chép thư mục dự án sang thiết bị biên thông qua giao thức SFTP/SCP:
```bash
# Ví dụ sao chép qua SCP
scp -r /d/CODE/yolo pi@<IP_THIET_BI_BIEN>:/home/pi/yolo
```

### Bước 2: Thiết lập môi trường Python ảo (Virtual Environment)
Đăng nhập vào thiết bị biên qua SSH, di chuyển vào thư mục dự án và khởi tạo môi trường ảo:
```bash
cd /home/pi/yolo
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt các thư viện dependencies tối ưu cho thiết bị biên

#### Đối với Raspberry Pi (Chỉ dùng CPU):
Cài đặt PyTorch tối ưu cho kiến trúc ARM64:
```bash
pip3 install --upgrade pip
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip3 install -r requirements.txt
```

#### Đối với NVIDIA Jetson (Tận dụng GPU CUDA):
Nên cài đặt PyTorch phiên bản dành riêng cho Jetson thông qua liên kết tải xuống của NVIDIA (do kiến trúc CUDA trên Jetson khác biệt với PC thông thường):
```bash
# Tham khảo tài liệu NVIDIA Jetson Zoo để tải file wheel phù hợp
pip3 install torch-*.whl
pip3 install -r requirements.txt
```

### Bước 4: Kết nối phần cứng và Cấu hình Camera nguồn vào
1. Cắm USB Camera (Webcam) hoặc lấy luồng camera IP (RTSP).
2. Kiểm tra danh sách camera khả dụng trên Linux:
   ```bash
   ls /dev/video*
   ```
3. Chỉnh sửa tệp cấu hình camera [cameras_config.json](file:///d:/CODE/yolo/cameras_config.json) trên thiết bị biên:
   * Nếu dùng USB Webcam: Đổi giá trị `"source"` thành chỉ số camera (Ví dụ: `0` hoặc `/dev/video0`).
   * Nếu dùng Camera IP: Đổi giá trị `"source"` thành URL luồng RTSP (Ví dụ: `rtsp://admin:password@192.168.1.100:554/stream`).

### Bước 5: Chạy ứng dụng Web Server
Thực thi lệnh khởi chạy máy chủ FastAPI (sử dụng Uvicorn):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
Bây giờ, bạn có thể truy cập Web Dashboard từ máy tính cá nhân bằng cách mở trình duyệt và gõ địa chỉ: `http://<IP_THIET_BI_BIEN>:8000`

---

## 3. Cấu hình Dịch vụ tự khởi động cùng Hệ điều hành (Systemd Service)

Để hệ thống tự động khởi chạy lại ngay khi thiết bị biên được cắm nguồn điện (chống mất điện đột ngột), hãy thiết lập một Systemd Service:

1. Tạo file cấu hình dịch vụ:
   ```bash
   sudo nano /etc/systemd/system/smart-camera.service
   ```
2. Dán nội dung cấu hình sau (điều chỉnh đường dẫn `/home/pi/yolo` tương ứng với thư mục của bạn):
   ```ini
   [Unit]
   Description=Smart Camera AI Surveillance System
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/yolo
   ExecStart=/home/pi/yolo/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Lưu file (`Ctrl+O`, `Enter`, `Ctrl+X`) và kích hoạt dịch vụ:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable smart-camera.service
   sudo systemctl start smart-camera.service
   ```
4. Kiểm tra trạng thái hoạt động của dịch vụ:
   ```bash
   sudo systemctl status smart-camera.service
   ```

Hệ thống sẽ chạy ngầm và tự động điều phối tài nguyên camera, tối ưu hóa suy luận học sâu trực tiếp tại nút biên thực tế mà không cần can thiệp thủ công!
