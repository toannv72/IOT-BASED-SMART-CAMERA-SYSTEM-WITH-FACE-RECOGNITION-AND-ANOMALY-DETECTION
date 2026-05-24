# Tài Liệu Hướng Dẫn Sử Dụng API - Hệ Thống Giám Sát AI

Tài liệu này mô tả chi tiết tất cả các điểm kết nối (endpoints) HTTP REST API và luồng dữ liệu (video stream) của hệ thống Giám sát Thông minh.

---

## 🔒 1. Xác Thực & Giao Diện (Authentication & Views)

Tất cả các trang giao diện HTML và endpoint API (ngoại trừ `/login` và `/register`) đều yêu cầu người dùng đã đăng nhập. Session được mã hóa an toàn qua cơ chế HMAC-SHA256 lưu trong Cookie tên là `surveillance_session`.

### 1.1 Đăng Nhập (Login)
*   **Trang Giao Diện:** `GET /login`
*   **Xử Lý Đăng Nhập:** `POST /login`
    -   **Kiểu dữ liệu gửi lên:** `application/x-www-form-urlencoded` (Form Data)
    -   **Tham số body:**
        -   `username` (string): Tên đăng nhập.
        -   `password` (string): Mật khẩu.
    -   **Kết quả trả về:** Chuyển hướng (Redirect 303) về trang chủ `/` nếu thành công, hoặc render lại trang login kèm thông báo lỗi.

### 1.2 Đăng Ký (Register)
*   **Trang Giao Diện:** `GET /register`
*   **Xử Lý Đăng Ký:** `POST /register`
    -   **Kiểu dữ liệu gửi lên:** `application/x-www-form-urlencoded` (Form Data)
    -   **Tham số body:**
        -   `username` (string): Tên đăng nhập mới.
        -   `password` (string): Mật khẩu.
    -   **Kết quả trả về:** Chuyển hướng sang trang đăng nhập nếu thành công.

### 1.3 Đăng Xuất (Logout)
*   **Yêu cầu:** `GET /logout`
*   **Kết quả trả về:** Xóa session cookie và chuyển hướng về `/login`.

### 1.4 Đường Dẫn Các Trang Giao Diện (Web Pages)
Mỗi menu liên kết tương ứng với một tệp HTML riêng biệt kế thừa từ `base.html`:
*   `GET /` : Màn hình Giám sát trực tuyến (`monitor.html`)
*   `GET /database` : Cơ sở dữ liệu khuôn mặt (`database.html`)
*   `GET /logs` : Nhật ký cảnh báo hệ thống (`logs.html`)
*   `GET /settings` : Cấu hình hệ thống & Quản lý camera (`settings.html`)
*   `GET /users` : Quản lý tài khoản quản trị (`users.html`)

---

## 📊 2. Trạng Thái Hệ Thống & Live Feed (System Health & Video Stream)

### 2.1 Lấy Thông Tin GPU
*   **Yêu cầu:** `GET /gpu_info`
*   **Kết quả trả về (JSON):**
    ```json
    {
      "gpu_name": "NVIDIA GeForce RTX 3060 Laptop GPU",
      "cuda_active": true
    }
    ```

### 2.2 Polling Trạng Thái Cảnh Báo Nhanh (System Status Polling)
Dùng để nhận biết khẩn cấp xem có xâm nhập ROI hoặc phát hiện ngã hay không, và lấy các thông báo log mới nhất.
*   **Yêu cầu:** `GET /system_status`
*   **Kết quả trả về (JSON):**
    ```json
    {
      "intrusion_alert": false,
      "fall_alert": true,
      "new_logs": [
        {
          "msg": "[CẢNH BÁO] Phát hiện có người ngã tại Cam_Hanh_Lang!",
          "type": "danger"
        }
      ]
    }
    ```

### 2.3 Giám Sát Hiệu Năng Chi Tiết (System Health)
*   **Yêu cầu:** `GET /api/system_health`
*   **Kết quả trả về (JSON):**
    ```json
    {
      "cpu_usage": 18.5,
      "ram_usage": 64.2,
      "gpu_active": true,
      "gpu_name": "NVIDIA GeForce RTX 3060 Laptop GPU",
      "gpu_usage": 32.0,
      "vram_allocated_mb": 1124.5,
      "vram_reserved_mb": 1850.0,
      "fps": {
        "Cam_Cua_Chinh": 24.5,
        "Cam_San_Sau": 12.0
      }
    }
    ```

### 2.4 Luồng Video Trực Tiếp (Video Feed Streaming)
*   **Yêu cầu:** `GET /video_feed/{camera_id}`
*   **Tham số Path:** `camera_id` (string) - ID của camera cần xem (ví dụ: `Cam_Cua_Chinh`).
*   **Kết quả trả về:** Stream hình ảnh chuyển động dạng `multipart/x-mixed-replace; boundary=frame`.

### 2.5 Chụp Khung Hình Hiện Tại (Backend Capture Bypass)
Dùng khi WebRTC trên trình duyệt bị lỗi HTTPS, cho phép lấy trực tiếp khung hình camera từ backend để đăng ký khuôn mặt.
*   **Yêu cầu:** `GET /api/capture_frame/{camera_id}`
*   **Tham số Path:** `camera_id` (string).
*   **Kết quả trả về:** Dữ liệu nhị phân ảnh JPEG (`image/jpeg`).

---

## 👤 3. Quản Lý Khuôn Mặt (Face Database Management)

### 3.1 Lấy Danh Sách Khuôn Mặt Đã Đăng Ký
*   **Yêu cầu:** `GET /faces`
*   **Kết quả trả về (JSON):**
    ```json
    [
      {
        "id": 1,
        "name": "Nguyen Van A",
        "created_at": "2026-05-24 15:30:22",
        "created_by": "admin"
      }
    ]
    ```

### 3.2 Đăng Ký Khuôn Mặt Mới
Trích xuất đặc trưng khuôn mặt (embedding) qua mạng nơ-ron MTCNN và FaceNet (ResNet) rồi lưu vào cơ sở dữ liệu.
*   **Yêu cầu:** `POST /register_face`
*   **Kiểu dữ liệu gửi lên:** `multipart/form-data`
*   **Tham số body:**
    -   `name` (string, required): Tên người đăng ký.
    -   `file` (file, required): File ảnh JPEG/PNG chứa khuôn mặt rõ nét.
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đăng ký thành công!",
      "id": 12,
      "name": "Nguyen Van A"
    }
    ```

### 3.3 Đổi Tên Khuôn Mặt Đăng Ký
*   **Yêu cầu:** `PUT /faces/{face_id}`
*   **Tham số Path:** `face_id` (integer).
*   **Kiểu dữ liệu gửi lên:** `application/json`
*   **Tham số body:**
    ```json
    {
      "name": "Nguyen Van A (Chỉnh sửa)"
    }
    ```
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã đổi tên thành công!"
    }
    ```

### 3.4 Xóa Khuôn Mặt Khỏi Hệ Thống
*   **Yêu cầu:** `DELETE /faces/{face_id}`
*   **Tham số Path:** `face_id` (integer).
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã xóa thành công!"
    }
    ```

---

## 🎛️ 4. Quản Lý Cấu Hình & Camera (System Configurations)

### 4.1 Lấy Cấu Hình Hệ Thống Cảnh Báo
*   **Yêu cầu:** `GET /api/settings`
*   **Kết quả trả về (JSON):**
    ```json
    {
      "telegram_token": "7291089201:AAH...",
      "telegram_chats": ["8438973190"],
      "conf_threshold": 0.25,
      "counter_cooldown": 45,
      "telegram_cooldown": 15,
      "alerts_enabled": true
    }
    ```

### 4.2 Cập Nhật Cấu Hình Hệ Thống
*   **Yêu cầu:** `POST /api/settings`
*   **Kiểu dữ liệu gửi lên:** `application/json`
*   **Tham số body:** Gửi lên một đối tượng JSON có các trường tương tự như kết quả trả về của `GET /api/settings` (chỉ cần truyền các trường muốn thay đổi).
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã cập nhật cài đặt!"
    }
    ```

### 4.3 Lấy Danh Sách Camera
*   **Yêu cầu:** `GET /api/cameras`
*   **Kết quả trả về (JSON):**
    ```json
    [
      {
        "camera_id": "Cam_Cua_Chinh",
        "source": "0",
        "features": ["people_counter", "face_id"],
        "line": [[100, 180], [540, 180]],
        "in_direction": "down",
        "roi": [[100, 100], [540, 100], [540, 300], [100, 300]],
        "schedule_enabled": false,
        "schedule_start": "23:00",
        "schedule_end": "06:00"
      }
    ]
    ```

### 4.4 Thêm Camera Mới
*   **Yêu cầu:** `POST /api/cameras`
*   **Kiểu dữ liệu gửi lên:** `application/json`
*   **Tham số body:**
    ```json
    {
      "camera_id": "Cam_San_Sau",
      "source": "video1.mp4",
      "features": ["intrusion_roi", "fall_detection"],
      "line": [[100, 180], [540, 180]],
      "roi": [[100, 100], [540, 100], [540, 300], [100, 300]],
      "schedule_enabled": true,
      "schedule_start": "22:00",
      "schedule_end": "05:00"
    }
    ```
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã thêm camera thành công!"
    }
    ```

### 4.5 Cập Nhật Cấu Hình Camera (Thay đổi nguồn, tính năng, hoặc tọa độ vạch/ROI)
*   **Yêu cầu:** `PUT /api/cameras/{camera_id}`
*   **Tham số Path:** `camera_id` (string).
*   **Kiểu dữ liệu gửi lên:** `application/json`
*   **Tham số body:** Đối tượng cấu hình camera đầy đủ (các trường tương tự như lúc tạo mới).
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã cập nhật camera thành công!"
    }
    ```

### 4.6 Xóa Camera Khỏi Hệ Thống
*   **Yêu cầu:** `DELETE /api/cameras/{camera_id}`
*   **Tham số Path:** `camera_id` (string).
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã xóa camera thành công!"
    }
    ```

---

## 👥 5. Quản Lý Tài Khoản Admin (User Account Management)

### 5.1 Lấy Danh Sách Admin
*   **Yêu cầu:** `GET /api/users`
*   **Kết quả trả về (JSON):**
    ```json
    [
      { "id": 1, "username": "admin" },
      { "id": 2, "username": "manager" }
    ]
    ```

### 5.2 Tạo Tài Khoản Admin Mới
*   **Yêu cầu:** `POST /api/users`
*   **Kiểu dữ liệu gửi lên:** `multipart/form-data` (Form Data)
*   **Tham số body:**
    -   `username` (string, required): Tên tài khoản.
    -   `password` (string, required): Mật khẩu.
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã tạo tài khoản quản trị thành công!"
    }
    ```

### 5.3 Thay Đổi Mật Khẩu Tài Khoản
*   **Yêu cầu:** `PUT /api/users/{user_id}`
*   **Tham số Path:** `user_id` (integer).
*   **Kiểu dữ liệu gửi lên:** `application/json`
*   **Tham số body:**
    ```json
    {
      "password": "new_password_here"
    }
    ```
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã đổi mật khẩu thành công!"
    }
    ```

### 5.4 Xóa Tài Khoản Admin (Không thể tự xóa chính mình)
*   **Yêu cầu:** `DELETE /api/users/{user_id}`
*   **Tham số Path:** `user_id` (integer).
*   **Kết quả trả về (JSON):**
    ```json
    {
      "message": "Đã xóa tài khoản thành công!"
    }
    ```

---

## 🗄️ 6. Nhật Ký Lưu Trữ SQLite (Event Logs Archive)

### 6.1 Lấy Lịch Sử Cảnh Báo (Tối đa 100 sự kiện mới nhất)
*   **Yêu cầu:** `GET /api/logs`
*   **Kết quả trả về (JSON):**
    ```json
    [
      {
        "id": 42,
        "event_type": "intrusion",
        "message": "Xâm nhập vùng cấm ROI tại camera Cam_San_Sau",
        "camera_id": "Cam_San_Sau",
        "image_path": "/static/alerts/intrusion_Cam_San_Sau_1716548902.jpg",
        "timestamp": "2026-05-24 15:48:22"
      }
    ]
    ```
