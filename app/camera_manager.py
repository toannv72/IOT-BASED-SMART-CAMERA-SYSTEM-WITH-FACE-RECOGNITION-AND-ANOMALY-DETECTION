import os
import sys
import time
import threading
import subprocess
import glob
import cv2
import numpy as np

# Khóa tuần tự hóa truy cập phần cứng DirectShow/V4L2 để ngăn chặn xung đột thiết bị
camera_hardware_lock = threading.Lock()

def open_safe_video_capture(source):
    """
    Mở an toàn thiết bị VideoCapture:
    - Sử dụng khóa độc quyền camera_hardware_lock để tránh xung đột DirectShow/COM.
    - Ép buộc codec MJPG để nén phần cứng trên webcam, giải phóng hoàn toàn băng thông bus USB
      khi cắm 2 hoặc nhiều webcam cùng lúc trên 1 máy tính.
    - Giới hạn buffer size = 1 để tránh trễ khung hình và giật lag.
    """
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    with camera_hardware_lock:
        if isinstance(source, int):
            backend = cv2.CAP_DSHOW if sys.platform.startswith('win') else None
            cap = cv2.VideoCapture(source, backend) if backend is not None else cv2.VideoCapture(source)
            if cap.isOpened():
                # 1. Bắt buộc MJPG để các webcam USB nén phần cứng, tránh nghẽn băng thông USB 2.0
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                # 2. Thiết lập độ phân giải tiêu chuẩn mượt mà
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # 3. Buffer = 1 để đọc khung hình mới nhất, không bị delay
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # 4. Tốc độ khung hình ổn định
                cap.set(cv2.CAP_PROP_FPS, 30)
                # Chờ 150ms để driver DirectShow ổn định filter graph
                time.sleep(0.15)
        else:
            cap = cv2.VideoCapture(source)

    return cap

def get_connected_camera_names():
    """
    Lấy danh sách tên thiết bị camera kết nối phần cứng trên hệ điều hành.
    Hỗ trợ Windows (PowerShell/PnP) và Linux/Raspberry Pi (v4l2-ctl).
    """
    names = []
    if sys.platform.startswith('win'):
        try:
            ps_script = 'Get-PnpDevice -Class Camera,Image | Where-Object { $_.Status -eq "OK" } | Select-Object -ExpandProperty FriendlyName'
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=4
            )
            if res.returncode == 0:
                lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                names = lines
        except Exception as e:
            print(f"[CAMERA MANAGER] Lỗi lấy tên camera Windows: {e}")
    elif sys.platform.startswith('linux'):
        try:
            res = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if res.returncode == 0:
                lines = res.stdout.splitlines()
                current_name = None
                for line in lines:
                    if not line.startswith("\t") and line.strip():
                        current_name = line.strip().rstrip(":")
                    elif "/dev/video" in line and current_name:
                        if current_name not in names:
                            names.append(current_name)
        except Exception as e:
            print(f"[CAMERA MANAGER] Lỗi lấy tên camera Linux: {e}")
            
    return names

def scan_system_cameras(active_cameras_config=None, camera_states=None):
    """
    Quét toàn bộ thiết bị webcam phần cứng và tệp video nội bộ.
    Đặc biệt: TUYỆT ĐỐI KHÔNG mở VideoCapture lên các cổng camera đang chạy
    để tránh xung đột phần cứng DirectShow.
    """
    from app import config
    if active_cameras_config is None:
        active_cameras_config = config.get_cameras_config()

    # Tạo bản đồ: source_str -> list các camera_id đang dùng
    source_to_cam = {}
    for c in active_cameras_config:
        src = str(c.get("source", "")).strip()
        if src:
            if src not in source_to_cam:
                source_to_cam[src] = []
            source_to_cam[src].append(c.get("camera_id", "Không rõ"))

    device_names = get_connected_camera_names()
    webcams = []

    # Danh sách thiết bị kết nối thực tế từ hệ điều hành
    # Mapping trực tiếp tên thiết bị sang các cổng 0, 1, 2...
    # Tuyệt đối KHÔNG mở VideoCapture trong quá trình quét để tránh xung đột phần cứng
    if not device_names:
        device_names = ["Camera chính (Webcam)", "Camera phụ 1 (USB)", "Camera phụ 2 (USB)"]

    for idx, dev_name in enumerate(device_names):
        src_str = str(idx)
        in_use_by = source_to_cam.get(src_str, [])
        webcams.append({
            "index": idx,
            "source": src_str,
            "name": f"{dev_name} (Cổng {idx})",
            "resolution": "640x480 (Chuẩn)",
            "working": True,
            "is_streaming": bool(in_use_by),
            "in_use_by": in_use_by
        })

    # Bổ sung thêm 1 cổng mở rộng nếu người dùng cắm thêm thiết bị khác
    next_idx = len(device_names)
    webcams.append({
        "index": next_idx,
        "source": str(next_idx),
        "name": f"Camera mở rộng / Ảo (Cổng {next_idx})",
        "resolution": "640x480",
        "working": True,
        "is_streaming": bool(source_to_cam.get(str(next_idx))),
        "in_use_by": source_to_cam.get(str(next_idx), [])
    })

    # Liệt kê các tệp video có sẵn trong thư mục gốc
    local_videos = []
    for ext in ("*.mp4", "*.avi", "*.mkv"):
        for f in glob.glob(ext):
            base_f = os.path.basename(f)
            local_videos.append({
                "source": base_f,
                "name": f"Tệp video: {base_f}",
                "in_use_by": source_to_cam.get(base_f, [])
            })

    return {
        "webcams": webcams,
        "local_videos": local_videos
    }

def get_camera_preview_image(source_str: str, camera_states=None):
    """
    Chụp một khung hình xem trước (preview thumbnail) cho một nguồn camera.
    - Nếu nguồn đang được một luồng nền sử dụng, lấy trực tiếp từ bộ nhớ đệm frame.
    - TUYỆT ĐỐI không mở lại VideoCapture trên cổng đang hoạt động để tránh xung đột phần cứng.
    - Nếu nguồn chưa được sử dụng, mở an toàn qua open_safe_video_capture và giải phóng ngay.
    """
    from app import config
    source_str = str(source_str).strip()

    # 1. Kiểm tra xem nguồn này có đang thuộc về camera nào đã cấu hình không
    cams = config.get_cameras_config()
    matched_cam = next((c for c in cams if str(c.get("source", "")).strip() == source_str), None)
    
    if matched_cam:
        cam_id = matched_cam.get("camera_id")
        if camera_states and cam_id in camera_states:
            st = camera_states[cam_id]
            if st.last_jpeg_frame is not None:
                return st.last_jpeg_frame
            elif st.last_frame is not None:
                thumb = cv2.resize(st.last_frame, (320, 180))
                ret_enc, buf = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret_enc:
                    return buf.tobytes()
        
        # Đang khởi chạy luồng nền, chưa có frame kịp thời
        blank = np.zeros((180, 320, 3), dtype=np.uint8)
        cv2.putText(blank, "DANG KHOI CHAY LUONG...", (30, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.putText(blank, f"Camera: {cam_id} (Cong {source_str})", (35, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        ret_enc, buf = cv2.imencode('.jpg', blank)
        return buf.tobytes() if ret_enc else None

    # 2. Nếu là webcam index hoàn toàn mới (chưa có camera nào dùng)
    if source_str.isdigit():
        idx = int(source_str)
        try:
            cap = open_safe_video_capture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                # Một số webcam USB cần 2-3 frame warmup ban đầu
                if not ret or frame is None:
                    for _ in range(4):
                        time.sleep(0.05)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            break
                cap.release()
                time.sleep(0.05)
                if ret and frame is not None:
                    thumb = cv2.resize(frame, (320, 180))
                    cv2.putText(thumb, f"CONG #{idx} (KHA DUNG)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                    ret_enc, buf = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if ret_enc:
                        return buf.tobytes()
        except Exception as e:
            print(f"[CAMERA MANAGER] Lỗi preview webcam {idx}: {e}")

    # 3. Nếu là tệp video cục bộ
    elif os.path.exists(source_str):
        try:
            cap = cv2.VideoCapture(source_str)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    thumb = cv2.resize(frame, (320, 180))
                    cv2.putText(thumb, f"FILE: {os.path.basename(source_str)}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    ret_enc, buf = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if ret_enc:
                        return buf.tobytes()
        except Exception as e:
            print(f"[CAMERA MANAGER] Lỗi preview video file {source_str}: {e}")

    # 4. Fallback: Ảnh báo không có tín hiệu
    blank = np.zeros((180, 320, 3), dtype=np.uint8)
    cv2.putText(blank, "KHONG CO TIN HIEU", (45, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    cv2.putText(blank, f"Nguon: {source_str}", (50, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    ret_enc, buf = cv2.imencode('.jpg', blank)
    return buf.tobytes() if ret_enc else None

