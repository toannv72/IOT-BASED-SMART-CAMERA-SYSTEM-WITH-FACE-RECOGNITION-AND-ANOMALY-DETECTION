# HƯỚNG DẪN CẤU HÌNH KHỞI CHẠY 1 NÚT & TỰ ĐỘNG CHẠY KHI CÓ ĐIỆN LẠI

Tài liệu này hướng dẫn cách cấu hình hệ thống **Smart Camera Edge AI** để:
1. **Chạy 1 nút bấm (1-Click)**: Không cần gõ lệnh terminal hay chọn menu phức tạp.
2. **Tự động chạy lại khi mất điện rồi có điện trở lại**: Thiết bị tự khởi động và phục hồi giám sát an ninh 100% tự động mà không cần người can thiệp.

---

## I. DÀNH CHO RASPBERRY PI 4 (THIẾT BỊ BIÊN THỰC TẾ)

### 1. Nguyên lý tự động phục hồi khi mất điện
* Bo mạch Raspberry Pi 4 **không có công tắc nguồn vật lý** (Hardware Power Switch). Khi cắm dây nguồn Type-C (hoặc khi mất điện rồi có điện lưới trở lại), bo mạch sẽ **tự động bật nguồn và khởi động hệ điều hành** (Auto Power-On).
* Thông qua dịch vụ ngầm **Systemd Service** (`smartcamera.service`), ngay sau khi hệ điều hành boot xong (~15-20 giây), hệ thống Smart Camera AI sẽ tự động được kích hoạt chạy ngầm, tự động kết nối webcam, cảm biến khí ga MQ-2, rơ-le khóa cửa và bot Telegram.

### 2. Cài đặt tự khởi động (Chỉ cần 1 lệnh duy nhất)
Đăng nhập vào Raspberry Pi qua SSH hoặc mở Terminal trong thư mục dự án, chạy lệnh:
```bash
sudo bash cai_dat_tu_khoi_dong_pi.sh
```

**Script này sẽ tự động thực hiện mọi việc:**
* Tự nhận diện thư mục dự án và môi trường ảo `venv` của bạn.
* Tự động cấu hình file dịch vụ `/etc/systemd/system/smartcamera.service`.
* Cấu hình cơ chế tự hồi phục `Restart=always` (nếu camera bị lỏng cáp hoặc ứng dụng gặp sự cố sẽ tự khởi động lại sau 5 giây).
* Bật cờ `systemctl enable` để tự khởi chạy trọn đời mỗi khi cấp điện.
* Khởi động ngay hệ thống mà không cần restart lại Pi.

### 3. Kiểm tra và Quản lý trên Raspberry Pi
* **Xem nhật ký hoạt động trực tiếp (Real-time logs):**
  ```bash
  journalctl -u smartcamera.service -f
  ```
* **Kiểm tra trạng thái dịch vụ:**
  ```bash
  sudo systemctl status smartcamera.service
  ```
* **Khởi động lại hệ thống:**
  ```bash
  sudo systemctl restart smartcamera.service
  ```
* **Dừng hoặc Hủy tự khởi động (khi không muốn tự chạy nữa):**
  ```bash
  sudo bash tat_tu_khoi_dong_pi.sh
  ```

### 4. Chạy 1-Click bằng tay trên màn hình Desktop của Pi
Nếu bạn cắm màn hình HDMI vào Pi và muốn nhấp chuột để chạy:
* Chỉ cần nhấp đúp vào file `chay_1_click.sh` trong thư mục dự án.

---

## II. DÀNH CHO MÁY TÍNH / LAPTOP WINDOWS (MÔI TRƯỜNG PHÁT TRIỂN & DEMO)

### Cách 1: Khởi chạy 1 nút bấm (1-Click Run)
* Trong thư mục dự án, bạn chỉ cần **nhấp đúp chuột vào file [CHAY_1_NUT.bat](file:///d:/CODE/yolo/CHAY_1_NUT.bat)**.
* **File này sẽ tự động:**
  1. Kiểm tra và tắt mọi tiến trình cũ đang chiếm cổng `8000` (tránh lỗi xung đột port).
  2. Khởi chạy máy chủ AI Smart Camera (`python main.py`).
  3. Tự động mở sẵn trình duyệt web truy cập `http://localhost:8000` sau 3 giây.
  *Bạn không cần phải gõ bất kỳ câu lệnh hay chọn menu số nào.*

### Cách 2: Tự động chạy khi mở máy tính / có điện lại
Nếu bạn muốn máy tính Windows khi bật nguồn lên hoặc khi mất điện có điện lại sẽ **tự động mở Smart Camera**:
1. Nhấp đúp chuột vào file **[cai_dat_tu_chay_windows.bat](file:///d:/CODE/yolo/cai_dat_tu_chay_windows.bat)**.
2. File sẽ tự động đăng ký shortcut vào thư mục `Startup` của Windows (`shell:startup`).
3. Từ nay, mỗi khi Windows khởi động xong, hệ thống Smart Camera sẽ tự động chạy lên màn hình!
4. Nếu muốn hủy tính năng này, chỉ cần nhấp đúp vào file **[huy_tu_chay_windows.bat](file:///d:/CODE/yolo/huy_tu_chay_windows.bat)**.

> [!TIP]
> **Đối với máy tính để bàn (PC/Desktop):** Để máy tính tự bật lên khi có điện lại sau sự cố mất điện, bạn có thể vào BIOS/UEFI của bo mạch chủ (nhấn `F2` hoặc `Delete` khi bật máy), tìm mục **Power Management / AC Back / Restore on AC/Power Loss** và chọn sang chế độ **Power On** (hoặc **Always On**).

---

## III. TÓM TẮT CÁC TỆP TIN ĐÃ ĐƯỢC TẠO MỚI

| Tệp tin | Hệ điều hành | Mô tả chức năng |
| :--- | :--- | :--- |
| **`cai_dat_tu_khoi_dong_pi.sh`** | Raspberry Pi / Linux | Script 1 lệnh tự cài Systemd service, tự chạy khi cắm điện. |
| **`tat_tu_khoi_dong_pi.sh`** | Raspberry Pi / Linux | Tắt dịch vụ tự khởi động khi không còn nhu cầu. |
| **`chay_1_click.sh`** | Raspberry Pi / Linux | Chạy 1 click trên màn hình Pi, tự mở trình duyệt. |
| **`CHAY_1_NUT.bat`** | Windows | Nhấp đúp 1 cái là tự giải phóng port, mở server & mở web. |
| **`cai_dat_tu_chay_windows.bat`** | Windows | Đăng ký tự khởi động cùng Windows khi bật máy. |
| **`huy_tu_chay_windows.bat`** | Windows | Hủy tự khởi động cùng Windows. |
