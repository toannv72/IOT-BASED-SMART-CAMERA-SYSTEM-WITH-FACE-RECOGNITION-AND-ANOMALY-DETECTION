import os
import cv2
import time
import math
import numpy as np
import json
import collections
from PIL import Image
import torch
import supervision as sv

# Import các biến cấu hình và mô hình AI từ các package
import threading
import app.config as config
from app.config import SystemStatus
from app.ai import device, mtcnn_multi, resnet, yolov5_model, yolov8_model, yolov8_pose_model, yolov8_fall_model, yolov8_fire_model
from app.alerts import send_telegram_alert
from app.database import SessionLocal, FaceRecord

# Khóa Lock dùng chung toàn cục để đồng bộ suy luận trên thiết bị biên CPU/GPU (Tránh xung đột/Nghẽn cổ chai)
gpu_lock = threading.Lock()

# Biến lưu trữ FPS đo được thời gian thực cho từng luồng camera
camera_fps = {
    "face": 0.0,
    "roi": 0.0,
    "fall": 0.0
}

# =========================================================================
# LUỒNG 1: LUỒNG NHẬN DIỆN KHUÔN MẶT (FACE RECOGNITION)
# =========================================================================
def gen_face_stream():
    # 1. Nạp trước các vector nhúng (embeddings) và tên từ database SQLite
    db = SessionLocal()
    records = db.query(FaceRecord).all()
    db.close()
    
    names = [r.name for r in records]
    db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
    if len(db_embeddings) > 0:
        norms = np.linalg.norm(db_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        db_embeddings = db_embeddings / norms
    
    # 2. Mở Camera chính diện (Webcam 0)
    import sys
    if sys.platform.startswith('win'):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[PROCESSORS] [ERROR] Không thể mở webcam cho luồng khuôn mặt!")
        return

    THRESHOLD = config.settings.get("face_threshold", 0.80)  # Ngưỡng Euclid distance sau chuẩn hóa L2 (tương đương cosine distance) để nhận diện người quen
    frame_cnt = 0
    print("[PROCESSORS] Khởi tạo thành công luồng nhận diện khuôn mặt.")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            break
            
        # Tự động nạp lại embeddings sau mỗi 60 frames để cập nhật đăng ký mới mà không cần khởi động lại
        frame_cnt += 1
        if frame_cnt % 60 == 0:
            db = SessionLocal()
            records = db.query(FaceRecord).all()
            db.close()
            names = [r.name for r in records]
            db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
            if len(db_embeddings) > 0:
                norms = np.linalg.norm(db_embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                db_embeddings = db_embeddings / norms

        # 3. Phát hiện khuôn mặt bằng MTCNN
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        with gpu_lock:
            with torch.no_grad():
                boxes, _ = mtcnn_multi.detect(img_pil)
        
        if boxes is not None:
            with gpu_lock:
                with torch.no_grad():
                    faces = mtcnn_multi(img_pil)
            if faces is not None:
                # Che khuất phần mặt dưới (45% từ dưới lên) để hỗ trợ nhận diện khẩu trang
                faces[:, :, 88:, :] = 0.0
                # Trích xuất đặc trưng embedding
                with gpu_lock:
                    with torch.no_grad():
                        embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                
                for box, emb in zip(boxes, embeddings):
                    x1, y1, x2, y2 = [int(b) for b in box]
                    best_match_name = "Unknown"
                    best_distance = float("inf")
                    
                    # Chuẩn hóa L2-norm cho vector nhúng hiện tại
                    norm_val = np.linalg.norm(emb)
                    if norm_val > 0:
                        emb = emb / norm_val
                    
                    # 4. So khớp khoảng cách Euclid/Cosine với CSDL
                    if len(db_embeddings) > 0:
                        distances = np.linalg.norm(db_embeddings - emb, axis=1)
                        min_idx = np.argmin(distances)
                        min_dist = distances[min_idx]
                        
                        if min_dist < THRESHOLD:
                            best_match_name = names[min_idx]
                            best_distance = min_dist
                            
                    # 5. Vẽ box và nhãn tên lên khung hình
                    color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    # 6. Kích hoạt cảnh báo Telegram bất đồng bộ nếu phát hiện người lạ
                    if best_match_name == "Unknown":
                        SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người lạ (Unknown) trước cửa!", "danger")
                        send_telegram_alert(
                            message="⚠️ [CẢNH BÁO FACE] Phát hiện người lạ (Unknown) xuất hiện tại Camera Nhận Diện Khuôn Mặt!",
                            frame=frame,
                            alert_type="face",
                            camera_id="Cam_Khuon_Mat"
                        )
        
        # 7. Nén thành file ảnh JPEG trả về cho trình duyệt
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: 
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        # Đo lường tốc độ khung hình
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["face"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 2: LUỒNG GIÁM SÁT XÂM NHẬP VÙNG CẤM (ROI INTRUSION)
# =========================================================================
def gen_roi_stream():
    video_path = "video1.mp4"
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[PROCESSORS] [ERROR] Không thể mở video ROI: {video_path}")
        return

    # Tải vùng đa giác ROI cấu hình từ file
    ROI_FILE = "roi_video.json"
    points = []
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                points = json.load(f)
        except Exception:
            pass
            
    if len(points) < 3:
        points = [[150, 150], [550, 150], [580, 450], [120, 450]]

    print("[PROCESSORS] Khởi tạo thành công luồng cảnh báo xâm nhập ROI.")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        # 1. Phát hiện người bằng YOLOv5s
        with gpu_lock:
            with torch.no_grad():
                results = yolov5_model(frame)
        detections = results.xyxy[0].cpu().numpy()
        
        person_in_roi = False
        
        # Vẽ đa giác ROI màu vàng lên hình
        pts = np.array(points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
        
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Chỉ lấy các hộp có độ tự tin cao hơn cấu hình động
            if conf < config.settings.get("conf_threshold", 0.25):
                continue
                
            # Điểm chân và điểm tâm người dùng để so khớp trong ROI
            check_points = [
                (int((x1 + x2) / 2), y2),
                (int((x1 + x2) / 2), int((y1 + y2) / 2))
            ]
            
            is_in_this_det = False
            for cp in check_points:
                if cv2.pointPolygonTest(np.array(points, np.int32), cp, False) >= 0:
                    is_in_this_det = True
                    break
                    
            if is_in_this_det:
                person_in_roi = True
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Đỏ khi xâm nhập
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Xanh khi ngoài ROI
                
            cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 2. Xử lý trạng thái cảnh báo xâm nhập
        if person_in_roi:
            SystemStatus.intrusion_active = True
            cv2.putText(frame, "CANH BAO: XAM NHAP ROI!", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người xâm nhập vùng cấm!", "danger")
            
            # Gửi cảnh báo Telegram bất đồng bộ (Thread) không treo luồng
            send_telegram_alert(
                message="⚠️ [CẢNH BÁO ROI] Phát hiện người xâm nhập trái phép vùng cấm bảo mật!",
                frame=frame,
                alert_type="intrusion",
                camera_id="Cam_Cua_Chinh_ROI"
            )
        else:
            SystemStatus.intrusion_active = False
            cv2.putText(frame, "Trang thai: Binh thuong", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: 
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["roi"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 4: LUỒNG PHÁT HIỆN NGÃ (FALL DETECTION)
# =========================================================================
def gen_fall_stream():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[PROCESSORS] [ERROR] Không thể mở webcam cho luồng phát hiện ngã! Sử dụng video làm dự phòng.")
        cap = cv2.VideoCapture("video.mp4")
        if not cap.isOpened():
            return

    print("[PROCESSORS] Khởi tạo thành công luồng phát hiện ngã.")
    fall_counter = 0
    
    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            time.sleep(0.03)
            continue
            
        fall_in_frame = False
        conf_thr = config.settings.get("conf_threshold", 0.25)
        
        # Nhận diện ngã ưu tiên mô hình custom tự train, nếu không sử dụng pose estimation dự phòng
        if yolov8_fall_model is not None:
            with gpu_lock:
                with torch.no_grad():
                    results = yolov8_fall_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].cpu().item())
                    conf = float(box.conf[0].cpu().item())
                    
                    if conf > conf_thr:
                        x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                        
                        if cls_id == 0:  # Lớp 0: Người bị Ngã
                            color = (0, 0, 255)
                            label = f"FALL ({conf:.2f})"
                            fall_in_frame = True
                        else:  # Lớp 1: Bình thường
                            color = (0, 255, 0)
                            label = f"Normal ({conf:.2f})"
                            
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        else:
            # Thuật toán dự phòng dựa trên YOLOv8-pose và góc cơ thể
            with gpu_lock:
                with torch.no_grad():
                    results = yolov8_pose_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].keypoints is not None:
                keypoints_data = results[0].keypoints.data.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                
                for i, kpts in enumerate(keypoints_data):
                    box = boxes[i]
                    x1, y1, x2, y2 = [int(b) for b in box[:4]]
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    
                    # Trích xuất các khớp
                    l_sho, r_sho = kpts[5], kpts[6]
                    l_hip, r_hip = kpts[11], kpts[12]
                    
                    has_conf = kpts.shape[1] == 3
                    
                    sho_x = (l_sho[0] + r_sho[0]) / 2
                    sho_y = (l_sho[1] + r_sho[1]) / 2
                    hip_x = (l_hip[0] + r_hip[0]) / 2
                    hip_y = (l_hip[1] + r_hip[1]) / 2
                    
                    sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                    hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0
                    
                    is_horizontal = False
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        dy = sho_y - hip_y
                        dx = sho_x - hip_x
                        angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                        if angle_body < 40 or angle_body > 140:
                            is_horizontal = True
                            
                    # Cảnh báo ngã khi tỉ lệ vàng của khung nằm ngang hoặc góc cơ thể nằm ngang
                    if is_horizontal or aspect_ratio > 1.4:
                        fall_in_frame = True
                        color = (0, 0, 255)
                        label = "FALL (Pose Detection)"
                    else:
                        color = (0, 255, 0)
                        label = "Normal (Pose Detection)"
                        
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 2. Xử lý logic cảnh báo người ngã
        if fall_in_frame:
            fall_counter += 1
            if fall_counter >= 12:  # Báo động khi ngã trên 1.2 giây
                SystemStatus.fall_active = True
                cv2.putText(frame, "CANH BAO: NGUOI NGA!", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người bị ngã hoặc nằm trên sàn!", "danger")
                send_telegram_alert(
                    message="⚠️ [CẢNH BÁO FALL] Cảnh báo nguy hiểm! Phát hiện người bị ngã hoặc nằm yên trên sàn nhà!",
                    frame=frame,
                    alert_type="fall",
                    camera_id="Cam_Phat_Hien_Nga"
                )
        else:
            fall_counter = max(0, fall_counter - 1)
            if fall_counter == 0:
                SystemStatus.fall_active = False

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["fall"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 5: HỢP NHẤT GIÁM SÁT ĐA KÊNH ĐỘNG (DYNAMIC N-CAMERA STREAM)
# =========================================================================
camera_states = {}
paused_cameras = {}

def pause_camera_alerts(camera_id: str, duration_minutes: int):
    paused_cameras[camera_id] = time.time() + duration_minutes * 60
    print(f"[PROCESSORS] Camera '{camera_id}' alerts paused for {duration_minutes} minutes.")

def resume_camera_alerts(camera_id: str):
    paused_cameras[camera_id] = 0
    print(f"[PROCESSORS] Camera '{camera_id}' alerts resumed immediately.")


class CameraState:
    def __init__(self):
        self.track_states = {}
        self.lost_tracks = {}
        self.active_tracks = {}
        self.frame_index = 0
        self.fall_counter = 0
        self.count_in = 0
        self.count_out = 0
        self.last_frame = None
        self.frame_buffer = collections.deque(maxlen=150)
        self.intrusion_entry_times = {}
        self.last_face_log_times = {}
        self.track_histories = {}           # tid -> collections.deque of (timestamp, bbox, center)
        self.track_first_seen = {}          # tid -> first_seen_timestamp
        self.track_face_status = {}         # tid -> name or "unknown"
        self.behavior_alert_cooldowns = {}  # tid -> last_alert_timestamp
        self.track_high_risk_start_times = {} # tid -> timestamp of when they first exceeded score 60
        self.intrusion_active = False
        self.fall_active = False
        self.fire_active = False
        self.fire_counter = 0
        self.last_jpeg_frame = None


def is_time_in_schedule(start_str, end_str):
    """
    Kiểm tra thời điểm hiện tại có nằm trong lịch trình từ start_str đến end_str hay không.
    Hỗ trợ hoàn hảo cả khung giờ vắt qua ngày hôm sau (Ví dụ: từ 23:00 đêm đến 06:00 sáng).
    """
    if not start_str or not end_str:
        return True
    try:
        from datetime import datetime
        now = datetime.now().time()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        if start_time <= end_time:
            return start_time <= now <= end_time
        else: # Qua đêm, ví dụ: 23:00 - 06:00
            return now >= start_time or now <= end_time
    except Exception:
        return True

def is_near_border(bbox, margin_x=60, margin_y=40):
    x1, y1, x2, y2 = bbox
    return (x1 < margin_x or x2 > 640 - margin_x or y1 < margin_y or y2 > 360 - margin_y)

import threading

camera_threads = {}
camera_stop_events = {}
camera_threads_lock = threading.Lock()

def ensure_camera_thread_running(camera_id: str):
    with camera_threads_lock:
        if camera_id in camera_threads and camera_threads[camera_id].is_alive():
            return
        
        stop_event = threading.Event()
        camera_stop_events[camera_id] = stop_event
        
        t = threading.Thread(
            target=camera_thread_worker,
            args=(camera_id, stop_event),
            daemon=True,
            name=f"CamBg_{camera_id}"
        )
        camera_threads[camera_id] = t
        t.start()
        print(f"[PROCESSORS] Spawned background thread for camera '{camera_id}'")

def camera_thread_worker(camera_id: str, stop_event: threading.Event):
    try:
        # Run the processing loop (which updates state.last_jpeg_frame)
        for _ in run_camera_processing_loop(camera_id, stop_event):
            if stop_event.is_set():
                break
    except Exception as e:
        print(f"[PROCESSORS] Error in background thread for camera '{camera_id}': {e}")
    finally:
        with camera_threads_lock:
            camera_threads.pop(camera_id, None)
            camera_stop_events.pop(camera_id, None)
        print(f"[PROCESSORS] Background thread for camera '{camera_id}' terminated.")

def stop_camera_thread(camera_id: str):
    with camera_threads_lock:
        if camera_id in camera_stop_events:
            camera_stop_events[camera_id].set()
            print(f"[PROCESSORS] Stopping background thread for camera '{camera_id}'")

def start_all_camera_threads():
    try:
        # Khởi chạy luồng giám sát cảm biến khí Ga MQ-2
        start_gas_sensor_monitoring()
        # Khởi chạy luồng còi báo động hệ thống
        start_buzzer_monitoring()
        
        cameras = config.get_cameras_config()
        for cam in cameras:
            camera_id = cam["camera_id"]
            ensure_camera_thread_running(camera_id)
    except Exception as e:
        print(f"[PROCESSORS] Error starting all camera threads: {e}")

def gen_dynamic_stream(camera_id: str):
    """
    Bộ sinh luồng xử lý ảnh camera động.
    Đọc khung hình đã được xử lý và mã hóa JPEG từ luồng chạy ngầm (background thread).
    """
    ensure_camera_thread_running(camera_id)
    
    if camera_id not in camera_states:
        camera_states[camera_id] = CameraState()
    state = camera_states[camera_id]
    
    consecutive_empty = 0
    while True:
        if state.last_jpeg_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + state.last_jpeg_frame + b'\r\n')
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            if consecutive_empty > 100:  # ~10 seconds of no frames
                ensure_camera_thread_running(camera_id)
                consecutive_empty = 0
        time.sleep(0.04) # ~25 FPS max

def run_camera_processing_loop(camera_id: str, stop_event=None):
    """
    Bộ sinh luồng xử lý ảnh camera động chạy thực tế (có thể chạy ngầm).
    Tự động giải quyết các tác vụ deep learning (YOLOv8 Counter, YOLOv5 ROI, MTCNN/FaceNet, YOLOv8-pose Fall)
    dựa trên tính năng (features) được cấu hình động trên Web Dashboard cho camera tương ứng.
    """
    cameras = config.get_cameras_config()
    cfg = next((c for c in cameras if c["camera_id"] == camera_id), None)
    if not cfg:
        print(f"[PROCESSORS] [ERROR] Không tìm thấy cấu hình cho camera: {camera_id}")
        return

    if camera_id not in camera_states:
        camera_states[camera_id] = CameraState()
    state = camera_states[camera_id]

    source = cfg["source"]
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    import sys
    if isinstance(source, int) and sys.platform.startswith('win'):
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[PROCESSORS] [ERROR] Không thể mở camera source {source} cho camera {camera_id}")
        return

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    db = SessionLocal()
    records = db.query(FaceRecord).all()
    db.close()
    names = [r.name for r in records]
    db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
    if len(db_embeddings) > 0:
        norms = np.linalg.norm(db_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        db_embeddings = db_embeddings / norms

    print(f"[PROCESSORS] Bắt đầu khởi chạy luồng dynamic camera: {camera_id}")

    # Biến phục vụ ghi hình toàn bộ (Full Video Recording)
    full_writer = None
    frames_written = 0
    full_video_filename = None

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            if isinstance(source, str) and os.path.exists(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                state.frame_index = 0
                state.track_states.clear()
                state.lost_tracks.clear()
                state.active_tracks.clear()
                continue
            else:
                time.sleep(0.5)
                continue

        state.frame_index += 1
        frame = cv2.resize(frame, (640, 360))

        if cfg.get("low_light_enhance", False):
            clip_limit = cfg.get("enhance_clip_limit", 2.0)
            try:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l_channel, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
                cl = clahe.apply(l_channel)
                limg = cv2.merge((cl, a, b))
                frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            except Exception as e:
                print(f"[PROCESSORS] Lỗi CLAHE: {e}")

        state.last_frame = frame.copy()

        if state.frame_index % 30 == 0:
            cameras = config.get_cameras_config()
            new_cfg = next((c for c in cameras if c["camera_id"] == camera_id), None)
            if new_cfg:
                if new_cfg.get("source") != cfg.get("source"):
                    print(f"[PROCESSORS] Camera '{camera_id}' source changed from '{cfg.get('source')}' to '{new_cfg.get('source')}'. Reopening...")
                    cap.release()
                    source = new_cfg["source"]
                    if isinstance(source, str) and source.isdigit():
                        source = int(source)
                    import sys
                    if isinstance(source, int) and sys.platform.startswith('win'):
                        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(source)
                cfg = new_cfg
            
            if "face_id" in cfg.get("features", []) or "abnormal_behavior" in cfg.get("features", []):
                db = SessionLocal()
                records = db.query(FaceRecord).all()
                db.close()
                names = [r.name for r in records]
                db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
                if len(db_embeddings) > 0:
                    norms = np.linalg.norm(db_embeddings, axis=1, keepdims=True)
                    norms[norms == 0] = 1.0
                    db_embeddings = db_embeddings / norms

        features = cfg.get("features", [])
        conf_thr = config.settings.get("conf_threshold", 0.25)
        fire_conf_thr = config.settings.get("fire_conf_threshold", 0.55)
        fire_frame_buf_thr = config.settings.get("fire_frame_buffer", 25)
        cooldown_thr = config.settings.get("counter_cooldown", 45)
        alerts_enabled = config.settings.get("alerts_enabled", True) and cfg.get("alerts_enabled", True)
        face_thr = config.settings.get("face_threshold", 0.80)

        is_paused = time.time() < paused_cameras.get(camera_id, 0)

        alert_allowed_by_schedule = True
        if cfg.get("schedule_enabled", False):
            alert_allowed_by_schedule = is_time_in_schedule(cfg.get("schedule_start", "00:00"), cfg.get("schedule_end", "24:00"))

        run_yolo = ("intrusion_roi" in features) or ("abnormal_behavior" in features)
        run_face = "face_id" in features or "abnormal_behavior" in features
        run_fall = "fall_detection" in features
        if not run_fall:
            state.fall_active = False

        run_fire = "fire_detection" in features
        if not run_fire:
            state.fire_active = False

        detections = None
        if run_yolo:
            with gpu_lock:
                with torch.no_grad():
                    results = yolov8_model.track(frame, persist=True, tracker="custom_bytetrack.yaml", conf=conf_thr, classes=[0], verbose=False, device=device)
            detections = sv.Detections.from_ultralytics(results[0])
            detections = detections[detections.class_id == 0]

        annotated_frame = frame.copy()

        if "intrusion_roi" in features and detections is not None:
            rois = cfg.get("rois", [cfg.get("roi", [[100, 100], [540, 100], [540, 300], [100, 300]])])
            person_in_roi = False
            active_tids_in_roi = set()

            for roi_poly in rois:
                pts = np.array(roi_poly, np.int32).reshape((-1, 1, 2))
                
                is_this_roi_violated = False
                if detections.tracker_id is not None and len(detections.tracker_id) == len(detections):
                    for idx, tid in enumerate(detections.tracker_id):
                        bbox = detections.xyxy[idx]
                        check_points = [
                            (int((bbox[0] + bbox[2]) / 2), int(bbox[3])),
                            (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))
                        ]
                        for cp in check_points:
                            if cv2.pointPolygonTest(pts, cp, False) >= 0:
                                # BỎ QUA nếu người này là người nhà
                                if state.track_face_status.get(tid) not in [None, "Unknown"]:
                                    continue
                                person_in_roi = True
                                is_this_roi_violated = True
                                active_tids_in_roi.add(tid)
                                break
                else:
                    for bbox in detections.xyxy:
                        check_points = [
                            (int((bbox[0] + bbox[2]) / 2), int(bbox[3])),
                            (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))
                        ]
                        for cp in check_points:
                            if cv2.pointPolygonTest(pts, cp, False) >= 0:
                                person_in_roi = True
                                is_this_roi_violated = True
                                break

                color = (0, 0, 255) if is_this_roi_violated else (0, 255, 255)
                cv2.polylines(annotated_frame, [pts], True, color, 2)

            loitering_detected = False
            current_time = time.time()
            loitering_threshold = config.settings.get("loitering_threshold", 10)

            for tid in active_tids_in_roi:
                if tid not in state.intrusion_entry_times:
                    state.intrusion_entry_times[tid] = current_time
                else:
                    elapsed = current_time - state.intrusion_entry_times[tid]
                    if elapsed > loitering_threshold:
                        loitering_detected = True
                        cv2.putText(annotated_frame, f"LẢNG VẢNG ID #{tid}: {int(elapsed)}s", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                        
                        if "abnormal_behavior" not in features:
                            if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện lảng vảng ID #{tid} quá {loitering_threshold} giây!", "danger")
                                send_telegram_alert(
                                    message=f"⚠️ [{camera_id}] Phát hiện người lảng vảng ID #{tid} ở lại vùng cấm {int(elapsed)} giây!",
                                    frame=frame,
                                    alert_type="intrusion",
                                    camera_id=camera_id,
                                    frame_buffer=list(state.frame_buffer)
                                )

            for tid in list(state.intrusion_entry_times.keys()):
                if tid not in active_tids_in_roi:
                    state.intrusion_entry_times.pop(tid, None)

            if person_in_roi:
                if "abnormal_behavior" not in features:
                    state.intrusion_active = True
                if not loitering_detected:
                    cv2.putText(annotated_frame, "CANH BAO XAM NHAP!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if "abnormal_behavior" not in features:
                        if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                            SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện xâm nhập vùng cấm!", "danger")
                            send_telegram_alert(
                                message=f"⚠️ [{camera_id}] Phát hiện người xâm nhập vùng cấm!",
                                frame=frame,
                                alert_type="intrusion",
                                camera_id=camera_id,
                                frame_buffer=list(state.frame_buffer)
                            )
            else:
                if "abnormal_behavior" not in features:
                    state.intrusion_active = False

        if run_face:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            with gpu_lock:
                with torch.no_grad():
                    boxes, _ = mtcnn_multi.detect(img_pil)
            if boxes is not None:
                with gpu_lock:
                    with torch.no_grad():
                        faces = mtcnn_multi(img_pil)
                if faces is not None:
                    # Che khuất phần mặt dưới (45% từ dưới lên) để hỗ trợ nhận diện khẩu trang
                    faces[:, :, 88:, :] = 0.0
                    with gpu_lock:
                        with torch.no_grad():
                            embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                    face_log_cooldown = config.settings.get("face_log_cooldown", 30)
                    current_time = time.time()
                    
                    for box, emb in zip(boxes, embeddings):
                        x_1, y_1, x_2, y_2 = [int(b) for b in box]
                        best_match_name = "Unknown"
                        best_distance = float("inf")
                        # Chuẩn hóa L2-norm cho vector nhúng hiện tại
                        norm_val = np.linalg.norm(emb)
                        if norm_val > 0:
                            emb = emb / norm_val

                        if len(db_embeddings) > 0:
                            distances = np.linalg.norm(db_embeddings - emb, axis=1)
                            min_idx = np.argmin(distances)
                            min_dist = distances[min_idx]
                            if min_dist < face_thr:
                                best_match_name = names[min_idx]
                                best_distance = min_dist

                        # Liên kết khuôn mặt với tracker_id của YOLOv8 bằng độ chồng khớp hình học (overlap)
                        overlap_tid = None
                        if detections is not None and detections.tracker_id is not None:
                            best_overlap = 0.0
                            for det_idx, tid in enumerate(detections.tracker_id):
                                px1, py1, px2, py2 = detections.xyxy[det_idx]
                                ix1 = max(x_1, px1)
                                iy1 = max(y_1, py1)
                                ix2 = min(x_2, px2)
                                iy2 = min(y_2, py2)
                                if ix2 > ix1 and iy2 > iy1:
                                    area = (ix2 - ix1) * (iy2 - iy1)
                                    face_area = (x_2 - x_1) * (y_2 - y_1)
                                    overlap_ratio = area / float(face_area)
                                    if overlap_ratio > 0.5 and overlap_ratio > best_overlap:
                                        best_overlap = overlap_ratio
                                        overlap_tid = tid
                        if overlap_tid is not None:
                            old_face = state.track_face_status.get(overlap_tid)
                            if old_face is None or old_face == "Unknown" or (best_match_name != "Unknown" and old_face != best_match_name):
                                state.track_face_status[overlap_tid] = best_match_name

                        if "face_id" in features:
                            color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                            cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                            text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                            cv2.putText(annotated_frame, text, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                            last_log_time = state.last_face_log_times.get(best_match_name, 0)
                            if current_time - last_log_time > face_log_cooldown:
                                state.last_face_log_times[best_match_name] = current_time
                                
                                if best_match_name == "Unknown":
                                    if "abnormal_behavior" not in features:
                                        if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                            SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện khuôn mặt lạ!", "danger")
                                            send_telegram_alert(
                                                message=f"⚠️ [{camera_id}] Phát hiện khuôn mặt lạ xuất hiện!",
                                                frame=frame,
                                                alert_type="face",
                                                camera_id=camera_id,
                                                frame_buffer=list(state.frame_buffer),
                                                face_name="Unknown"
                                            )
                                else:
                                    if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                        SystemStatus.add_log(f"👤 {camera_id}: Nhận diện thành công khuôn mặt: {best_match_name}", "info")
                                        send_telegram_alert(
                                            message=f"👤 [{camera_id}] Nhận diện thành công khuôn mặt: {best_match_name}",
                                            frame=frame,
                                            alert_type="face",
                                            camera_id=camera_id,
                                            frame_buffer=list(state.frame_buffer),
                                            face_name=best_match_name
                                        )

        if "abnormal_behavior" in features:
            current_time = time.time()
            is_night = False
            try:
                from datetime import datetime
                current_hour = datetime.now().hour
                is_night = (current_hour >= 22) or (current_hour < 5)
            except Exception:
                pass

            if not hasattr(state, "track_high_risk_start_times"):
                state.track_high_risk_start_times = {}

            any_intrusion_active = False

            if detections is None or detections.tracker_id is None:
                state.intrusion_active = False
                if hasattr(state, "track_histories"):
                    state.track_histories.clear()
                    state.track_first_seen.clear()
                    state.track_face_status.clear()
                    state.behavior_alert_cooldowns.clear()
                    state.track_high_risk_start_times.clear()
            else:
                active_tids = set()
                for det_idx, tid in enumerate(detections.tracker_id):
                    active_tids.add(tid)
                    bbox = detections.xyxy[det_idx]
                    center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
                    
                    if tid not in state.track_histories:
                        state.track_histories[tid] = collections.deque(maxlen=150)
                        state.track_first_seen[tid] = current_time
                        if tid not in state.track_face_status:
                            state.track_face_status[tid] = None
                        
                        # Kiểm tra bàn giao người nhà từ camera khác nếu đối tượng mới xuất hiện sát biên
                        if is_near_border(bbox):
                            handover_name = SystemStatus.find_matching_handover(camera_id, current_time)
                            if handover_name:
                                state.track_face_status[tid] = handover_name
                                print(f"[CROSS-CAM] Bàn giao thành công: Đối tượng ID #{tid} trên '{camera_id}' thừa hưởng trạng thái người nhà '{handover_name}'")
                            
                    state.track_histories[tid].append((current_time, bbox, center))
                    
                # Dọn dẹp tracks cũ nếu không xuất hiện liên tục quá 3.0 giây
                for tid in list(state.track_histories.keys()):
                    history = state.track_histories[tid]
                    if history:
                        last_seen_time = history[-1][0]
                        if current_time - last_seen_time > 3.0:
                            state.track_histories.pop(tid, None)
                            state.track_first_seen.pop(tid, None)
                            state.track_face_status.pop(tid, None)
                            state.behavior_alert_cooldowns.pop(tid, None)
                            state.track_high_risk_start_times.pop(tid, None)
                    else:
                        state.track_histories.pop(tid, None)
                        state.track_first_seen.pop(tid, None)
                        state.track_face_status.pop(tid, None)
                        state.behavior_alert_cooldowns.pop(tid, None)
                        state.track_high_risk_start_times.pop(tid, None)
                        
                # Đánh giá hành vi của từng đối tượng
                for det_idx, tid in enumerate(detections.tracker_id):
                    bbox = detections.xyxy[det_idx]
                    x1_b, y1_b, x2_b, y2_b = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    
                    score = 0
                    reasons = []
                    
                    # 1. Ban đêm (+20)
                    if is_night:
                        score += 20
                        reasons.append("Ban Dem")
                        
                    # 2. Vùng cấm (+40)
                    rois = cfg.get("rois", [cfg.get("roi", [[100, 100], [540, 100], [540, 300], [100, 300]])])
                    in_roi = False
                    check_points = [
                        (int((bbox[0] + bbox[2]) / 2), int(bbox[3])),  # Điểm chân
                        (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))  # Trọng tâm
                    ]
                    for roi_poly in rois:
                        pts = np.array(roi_poly, np.int32).reshape((-1, 1, 2))
                        for cp in check_points:
                            if cv2.pointPolygonTest(pts, cp, False) >= 0:
                                in_roi = True
                                break
                        if in_roi: break
                        
                    if in_roi:
                        score += 40
                        reasons.append("Vung Cam")
                        
                    # 3. Đứng quá lâu (+20)
                    trajectory = state.track_histories.get(tid, [])
                    first_seen = state.track_first_seen.get(tid, current_time)
                    duration = current_time - first_seen
                    is_standing = False
                    if duration > 8.0:
                        recent_pts = [p for t_val, b_val, p in trajectory if current_time - t_val <= 8.0]
                        if recent_pts:
                            xs = [p[0] for p in recent_pts]
                            ys = [p[1] for p in recent_pts]
                            max_disp = math.sqrt((max(xs) - min(xs))**2 + (max(ys) - min(ys))**2)
                            if max_disp < 30.0:
                                is_standing = True
                    if is_standing:
                        score += 20
                        reasons.append("Dung Lau")
                        
                    # 4. Chạy nhanh (+10)
                    recent_1_5s = [item for item in trajectory if current_time - item[0] <= 1.5]
                    if len(recent_1_5s) >= 2:
                        t_diff = recent_1_5s[-1][0] - recent_1_5s[0][0]
                        if t_diff > 0.1:
                            dist = math.dist(recent_1_5s[-1][2], recent_1_5s[0][2])
                            speed = dist / t_diff
                            if speed > 120.0:
                                is_running = True
                    if is_running:
                        score += 10
                        reasons.append("Chay Nhanh")
                        
                    # 5. Leo rào (+50)
                    is_climbing = False
                    if len(recent_1_5s) >= 2:
                        t0_val, bbox0_val, p0_val = recent_1_5s[0]
                        t1_val, bbox1_val, p1_val = recent_1_5s[-1]
                        dt_val = t1_val - t0_val
                        if dt_val > 0.2:
                            v_y_val = (p1_val[1] - p0_val[1]) / dt_val
                            h0_val = bbox0_val[3] - bbox0_val[1]
                            h1_val = bbox1_val[3] - bbox1_val[1]
                            if abs(v_y_val) > 70.0 or (abs(h1_val - h0_val) / max(h0_val, 1) > 0.40):
                                is_climbing = True
                    if is_climbing:
                        score += 50
                        reasons.append("Leo Rao")
                        
                    # 6. Người lạ / Không nhận dạng được mặt (+15)
                    face_status = state.track_face_status.get(tid)
                    is_family_member = (face_status is not None) and (face_status != "Unknown")
                    
                    if is_family_member:
                        # Cập nhật bàn giao nếu là người nhà và đang ở sát biên
                        if is_near_border(bbox):
                            SystemStatus.add_handover(camera_id, face_status, current_time)
                        score = 0
                        reasons = [f"Nguoi Nha ({face_status})"]
                    else:
                        score += 15
                        reasons.append("Nguoi La")
                        
                    # Phân loại rủi ro
                    if is_family_member:
                        status = f"Nguoi Nha ({face_status})"
                        color = (0, 255, 0)
                    elif score < 30:
                        status = "Normal"
                        color = (0, 255, 0)
                    elif score <= 60:
                        status = "Suspicious"
                        color = (0, 165, 255)
                    else:
                        status = "Intrusion Alert"
                        color = (0, 0, 255)
                        
                    # Vẽ hộp bao và nhãn rủi ro lên khung hình
                    cv2.rectangle(annotated_frame, (x1_b, y1_b), (x2_b, y2_b), color, 2)
                    label_text = f"ID #{tid} | Risk: {score} ({status})"
                    cv2.putText(annotated_frame, label_text, (x1_b, y1_b - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    if reasons:
                        behavior_str = ", ".join(reasons)
                        cv2.putText(annotated_frame, f"Beh: {behavior_str}", (x1_b, y2_b + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                        
                    # Gửi cảnh báo Telegram bất đồng bộ nếu rủi ro cực cao (Cảnh báo trễ 5 giây)
                    if score > 60:
                        if tid not in state.track_high_risk_start_times:
                            state.track_high_risk_start_times[tid] = current_time
                            
                        high_risk_duration = current_time - state.track_high_risk_start_times[tid]
                        
                        if high_risk_duration < 5.0:
                            countdown = 5 - int(high_risk_duration)
                            cv2.putText(annotated_frame, f"Xác minh: {countdown}s...", (x1_b, y2_b + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)
                        else:
                            any_intrusion_active = True
                            last_alert_t = state.behavior_alert_cooldowns.get(tid, 0)
                            telegram_cooldown = config.settings.get("telegram_cooldown", 15)
                            
                            if current_time - last_alert_t > telegram_cooldown:
                                state.behavior_alert_cooldowns[tid] = current_time
                                
                                log_msg = f"⚠️ CẢNH BÁO: Phát hiện hành vi đột nhập bất thường từ ID #{tid} (Rủi ro: {score}). Chi tiết: {', '.join(reasons)}."
                                SystemStatus.add_log(log_msg, "danger")
                                
                                if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                    send_telegram_alert(
                                        message=f"🚨 [CẢNH BÁO ĐỘT NHẬP] Phát hiện hành vi bất thường từ đối tượng ID #{tid}!\n\nĐiểm rủi ro: {score} / 100\nChi tiết vi phạm: {', '.join(reasons)}",
                                        frame=frame,
                                        alert_type="intrusion",
                                        camera_id=camera_id,
                                        frame_buffer=list(state.frame_buffer)
                                    )
                    else:
                        state.track_high_risk_start_times.pop(tid, None)
                                
            # Vẽ nét mỏng vùng đa giác ROI của tính năng hành vi
            rois = cfg.get("rois", [cfg.get("roi", [[100, 100], [540, 100], [540, 300], [100, 300]])])
            for roi_poly in rois:
                pts = np.array(roi_poly, np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated_frame, [pts], True, (0, 255, 255), 1)

            state.intrusion_active = any_intrusion_active

        if run_fall:
            fall_in_frame = False
            if yolov8_fall_model is not None:
                with gpu_lock:
                    with torch.no_grad():
                        results = yolov8_fall_model(frame, verbose=False, device=device)
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].cpu().item())
                        conf = float(box.conf[0].cpu().item())
                        if conf > conf_thr:
                            x_1, y_1, x_2, y_2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                            if cls_id == 0:
                                fall_in_frame = True
                                color = (0, 0, 255)
                                label = f"FALL ({conf:.2f})"
                            else:
                                color = (0, 255, 0)
                                label = f"Normal ({conf:.2f})"
                            cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                            cv2.putText(annotated_frame, label, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            else:
                with gpu_lock:
                    with torch.no_grad():
                        results = yolov8_pose_model(frame, verbose=False, device=device)
                if len(results) > 0 and results[0].keypoints is not None:
                    keypoints_data = results[0].keypoints.data.cpu().numpy()
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    for i, kpts in enumerate(keypoints_data):
                        box = boxes[i]
                        x_1, y_1, x_2, y_2 = [int(b) for b in box[:4]]
                        w = x_2 - x_1
                        h = y_2 - y_1
                        aspect_ratio = w / (h + 1e-5)

                        l_sho, r_sho = kpts[5], kpts[6]
                        l_hip, r_hip = kpts[11], kpts[12]
                        has_conf = kpts.shape[1] == 3

                        sho_x = (l_sho[0] + r_sho[0]) / 2
                        sho_y = (l_sho[1] + r_sho[1]) / 2
                        hip_x = (l_hip[0] + r_hip[0]) / 2
                        hip_y = (l_hip[1] + r_hip[1]) / 2

                        sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                        hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0

                        is_horizontal = False
                        if sho_conf > 0.3 and hip_conf > 0.3:
                            dy = sho_y - hip_y
                            dx = sho_x - hip_x
                            angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                            if angle_body < 40 or angle_body > 140:
                                is_horizontal = True

                        if is_horizontal or aspect_ratio > 1.4:
                            fall_in_frame = True
                            color = (0, 0, 255)
                            label = "FALL (Pose)"
                        else:
                            color = (0, 255, 0)
                            label = "Normal (Pose)"
                        cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                        cv2.putText(annotated_frame, label, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if fall_in_frame:
                state.fall_counter += 1
                if state.fall_counter >= 12:
                    state.fall_active = True
                    cv2.putText(annotated_frame, "PHÁT HIỆN NGÃ!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                        SystemStatus.add_log(f"🚨 {camera_id}: Phát hiện người bị ngã!", "danger")
                        send_telegram_alert(
                            message=f"🚨 [{camera_id}] Phát hiện có người bị ngã!",
                            frame=frame,
                            alert_type="fall",
                            camera_id=camera_id,
                            frame_buffer=list(state.frame_buffer)
                        )
            else:
                state.fall_counter = max(0, state.fall_counter - 1)
                if state.fall_counter == 0:
                    state.fall_active = False

        if run_fire:
            fire_in_frame = False
            if yolov8_fire_model is not None:
                with gpu_lock:
                    with torch.no_grad():
                        results = yolov8_fire_model(frame, verbose=False, device=device)
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].cpu().item())
                        conf = float(box.conf[0].cpu().item())
                        if conf > fire_conf_thr:
                            x_1, y_1, x_2, y_2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                            label_name = yolov8_fire_model.names.get(cls_id, f"Class {cls_id}").capitalize()
                            
                            if "fire" in label_name.lower():
                                color = (0, 0, 255)
                                fire_in_frame = True
                            elif "smoke" in label_name.lower():
                                color = (128, 128, 128)
                                fire_in_frame = True
                            else:
                                color = (0, 165, 255)
                                fire_in_frame = True
                                
                            label = f"{label_name} ({conf:.2f})"
                            cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                            cv2.putText(annotated_frame, label, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if fire_in_frame:
                state.fire_counter += 1
                if state.fire_counter >= fire_frame_buf_thr:
                    state.fire_active = True
                    cv2.putText(annotated_frame, "🚨 PHÁT HIỆN CHÁY NỔ!", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                        SystemStatus.add_log(f"🚨 {camera_id}: Phát hiện ngọn lửa hoặc khói bất thường!", "danger")
                        send_telegram_alert(
                            message=f"🚨 [{camera_id}] Cảnh báo: Phát hiện ngọn lửa hoặc khói bất thường tại camera!",
                            frame=frame,
                            alert_type="fire",
                            camera_id=camera_id,
                            frame_buffer=list(state.frame_buffer)
                        )
            else:
                state.fire_counter = max(0, state.fire_counter - 1)
                if state.fire_counter == 0:
                    state.fire_active = False

        # Cập nhật trạng thái hệ thống dùng chung từ tất cả các camera để tránh xung đột ghi đè
        SystemStatus.intrusion_active = any(s.intrusion_active for s in camera_states.values())
        SystemStatus.fall_active = any(s.fall_active for s in camera_states.values())
        SystemStatus.fire_active = any(s.fire_active for s in camera_states.values())

        # Trạng thái lịch trình
        if not alert_allowed_by_schedule:
            cv2.putText(annotated_frame, "Cảnh báo tắt (Theo Lịch Trình)", (10, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Lưu khung hình kèm nét vẽ AI vào bộ đệm để ghi video sự cố
        state.frame_buffer.append(annotated_frame.copy())

        # Ghi hình toàn bộ (Continuous Video Recording)
        record_full = config.settings.get("record_full_video", False)
        if record_full:
            if full_writer is None:
                try:
                    os.makedirs("static/recordings", exist_ok=True)
                    from datetime import datetime
                    from app.alerts import sanitize_filename_component
                    sanitized_cam = sanitize_filename_component(camera_id)
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    full_video_filename = f"recording_{sanitized_cam}_{timestamp_str}.mp4"
                    filepath = os.path.join("static", "recordings", full_video_filename)
                    
                    # Thử mở trình ghi video với các codec khác nhau
                    fourcc = cv2.VideoWriter_fourcc(*'avc1')
                    full_writer = cv2.VideoWriter(filepath, fourcc, 15.0, (640, 360))
                    
                    if not full_writer.isOpened():
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        full_writer = cv2.VideoWriter(filepath, fourcc, 15.0, (640, 360))
                        
                    if not full_writer.isOpened():
                        # Thử ghi định dạng AVI bằng codec XVID nếu MP4 thất bại
                        full_video_filename = f"recording_{sanitized_cam}_{timestamp_str}.avi"
                        filepath = os.path.join("static", "recordings", full_video_filename)
                        fourcc = cv2.VideoWriter_fourcc(*'XVID')
                        full_writer = cv2.VideoWriter(filepath, fourcc, 15.0, (640, 360))
                        
                    if not full_writer.isOpened():
                        # Thử codec MJPG
                        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                        full_writer = cv2.VideoWriter(filepath, fourcc, 15.0, (640, 360))
                        
                    if not full_writer.isOpened():
                        print(f"[RECORDING] [ERROR] Không thể khởi tạo bất kỳ codec nào cho camera '{camera_id}'!")
                        full_writer = None
                    else:
                        frames_written = 0
                        print(f"[RECORDING] Khởi tạo thành công trình ghi cho camera '{camera_id}': {full_video_filename}")
                except Exception as e:
                    print(f"[RECORDING] Lỗi khởi tạo trình ghi video: {e}")
                    full_writer = None
            
            if full_writer is not None:
                try:
                    full_writer.write(annotated_frame)
                    frames_written += 1
                    
                    # Tách file sau mỗi 10 phút (ở 15 FPS = 9000 frames)
                    if frames_written >= 9000:
                        print(f"[RECORDING] Đạt giới hạn 10 phút. Tách tệp ghi hình cho camera '{camera_id}'.")
                        full_writer.release()
                        full_writer = None
                except Exception as e:
                    print(f"[RECORDING] Lỗi ghi khung hình: {e}")
        else:
            if full_writer is not None:
                try:
                    full_writer.release()
                    print(f"[RECORDING] Dừng ghi hình toàn bộ cho camera '{camera_id}' (Tắt option).")
                except Exception:
                    pass
                full_writer = None

        ret_enc, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret_enc: continue

        state.last_jpeg_frame = buffer.tobytes()

        try:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + state.last_jpeg_frame + b'\r\n')
        except GeneratorExit:
            if full_writer is not None:
                try:
                    full_writer.release()
                    print(f"[RECORDING] Giải phóng trình ghi video cho camera '{camera_id}' khi đóng generator (GeneratorExit).")
                except Exception:
                    pass
            cap.release()
            raise

        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps[camera_id] = round(fps, 1)

        if stop_event is not None:
            if stop_event.is_set():
                break
            # Giới hạn tốc độ gửi về client khoảng 25 FPS để giảm tải CPU cho các file video tĩnh
            elapsed = t_end - t_start
            delay = max(0.005, 0.04 - elapsed)
            time.sleep(delay)

    if full_writer is not None:
        try:
            full_writer.release()
            print(f"[RECORDING] Giải phóng trình ghi video cho camera '{camera_id}' khi dừng luồng.")
        except Exception:
            pass
    cap.release()

# =========================================================================
# PHÂN HỆ CẢM BIẾN KHÍ GA MQ-2 (ĐỒNG BỘ CHO THIẾT BỊ BIÊN RASPBERRY PI 4)
# =========================================================================
gas_monitoring_active = False

def start_gas_sensor_monitoring():
    global gas_monitoring_active
    if gas_monitoring_active:
        return
    gas_monitoring_active = True
    
    t = threading.Thread(target=_gas_sensor_loop, daemon=True)
    t.start()
    print("[GAS SENSOR] Bắt đầu khởi chạy luồng nền giám sát cảm biến khí Ga.")

def _gas_sensor_loop():
    has_gpio = False
    try:
        import RPi.GPIO as GPIO
        has_gpio = True
    except ImportError:
        print("[GAS SENSOR] [WARNING] RPi.GPIO không khả dụng (Chạy chế độ giả lập).")
        
    GAS_PIN = 18 # GPIO 18 (Pin 12)
    
    if has_gpio:
        try:
            GPIO.setmode(GPIO.BCM)
            # MQ-2 DO pin outputs LOW (0) when gas is detected, or HIGH (1) when clean.
            # We configure pull-up to keep it stable.
            GPIO.setup(GAS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            print(f"[GAS SENSOR] [ERROR] Không thể khởi tạo GPIO: {e}")
            has_gpio = False

    cooldown = 0
    while True:
        try:
            if has_gpio:
                is_gas_detected = (GPIO.input(GAS_PIN) == GPIO.LOW)
            else:
                # Đọc trạng thái giả lập từ SystemStatus
                is_gas_detected = getattr(SystemStatus, "mock_gas_leak", False)
                
            if is_gas_detected:
                if not SystemStatus.gas_active:
                    SystemStatus.gas_active = True
                    SystemStatus.add_log("🚨 CẢNH BÁO: Phát hiện rò rỉ khí GA tại cảm biến MQ-2!", "danger")
                
                # Gửi cảnh báo Telegram với cooldown 30 giây tránh spam
                if time.time() - cooldown > 30:
                    cooldown = time.time()
                    try:
                        send_telegram_alert(
                            message="🚨 [CẢNH BÁO NGUY HIỂM]\nPhát hiện sự cố RÒ RỈ KHÍ GA tại cảm biến biên MQ-2!",
                            alert_type="gas"
                        )
                    except Exception as e:
                        print(f"[GAS SENSOR] [ERROR] Lỗi gửi tin Telegram: {e}")
            else:
                if SystemStatus.gas_active:
                    SystemStatus.gas_active = False
                    SystemStatus.add_log("💨 Trạng thái khí ga đã trở về mức an toàn.", "success")
                    
            time.sleep(1.0)
        except Exception as e:
            print(f"[GAS SENSOR] Lỗi vòng lặp giám sát: {e}")
            time.sleep(5.0)

# =========================================================================
# PHÂN HỆ ĐIỀU KHIỂN KHÓA CỬA TỰ ĐỘNG (SOLENOID DOOR LOCK VIA GPIO)
# =========================================================================
def unlock_door():
    """Kích hoạt mở khóa cửa bằng luồng nền bất đồng bộ"""
    t = threading.Thread(target=_unlock_door_worker, daemon=True)
    t.start()

def _unlock_door_worker():
    # Tránh kích hoạt trùng lặp khi cửa đang mở
    if SystemStatus.door_unlock_active:
        return
        
    SystemStatus.door_unlock_active = True
    SystemStatus.add_log("🔑 HỆ THỐNG: Đang kích hoạt mở khóa cửa (3 giây)...", "info")
    
    has_gpio = False
    try:
        import RPi.GPIO as GPIO
        has_gpio = True
    except ImportError:
        pass
        
    UNLOCK_PIN = 23 # GPIO 23 (Pin 16)
    
    if has_gpio:
        try:
            orig_mode = GPIO.getmode()
            if orig_mode is None:
                GPIO.setmode(GPIO.BCM)
                
            GPIO.setup(UNLOCK_PIN, GPIO.OUT)
            # Kích hoạt Relay mở khóa (HIGH)
            GPIO.output(UNLOCK_PIN, GPIO.HIGH)
            print(f"[DOOR LOCK] GPIO {UNLOCK_PIN} set to HIGH (Door Unlocked).")
        except Exception as e:
            print(f"[DOOR LOCK] [ERROR] Lỗi điều khiển GPIO mở cửa: {e}")
            has_gpio = False

    # Giữ cửa mở trong 3 giây
    time.sleep(3.0)
    
    if has_gpio:
        try:
            GPIO.output(UNLOCK_PIN, GPIO.LOW)
            print(f"[DOOR LOCK] GPIO {UNLOCK_PIN} set to LOW (Door Locked).")
        except Exception as e:
            print(f"[DOOR LOCK] [ERROR] Lỗi khóa cửa GPIO: {e}")
            
    SystemStatus.door_unlock_active = False
    SystemStatus.add_log("🔒 HỆ THỐNG: Cửa đã tự động khóa lại.", "muted")

# =========================================================================
# PHÂN HỆ CÒI BÁO ĐỘNG HỆ THỐNG (ALARM BUZZER VIA GPIO 24)
# =========================================================================
buzzer_thread_started = False

def start_buzzer_monitoring():
    global buzzer_thread_started
    if buzzer_thread_started:
        return
    buzzer_thread_started = True
    t = threading.Thread(target=_buzzer_control_loop, daemon=True)
    t.start()
    print("[BUZZER] Bắt đầu khởi chạy luồng nền giám sát và nháy còi báo động.")

def _buzzer_control_loop():
    has_gpio = False
    try:
        import RPi.GPIO as GPIO
        has_gpio = True
    except ImportError:
        pass
        
    BUZZER_PIN = 24 # GPIO 24 (Pin 18)
    
    if has_gpio:
        try:
            orig_mode = GPIO.getmode()
            if orig_mode is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUZZER_PIN, GPIO.OUT)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        except Exception as e:
            print(f"[BUZZER] [ERROR] Lỗi cấu hình GPIO còi: {e}")
            has_gpio = False

    while True:
        try:
            # 1. Xác định điều kiện kích hoạt báo động
            is_fire = SystemStatus.fire_active
            is_gas = SystemStatus.gas_active
            is_mock = getattr(SystemStatus, "mock_buzzer", False)
            
            # Kiểm tra chế độ khóa nhà và xâm nhập tại các camera được cấu hình
            is_intrusion_alarm = False
            house_locked = config.settings.get("house_locked", False)
            if house_locked:
                cameras = config.get_cameras_config()
                for cam in cameras:
                    cam_id = cam["camera_id"]
                    if cam.get("trigger_alarm", False):
                        state = camera_states.get(cam_id)
                        if state and getattr(state, "intrusion_active", False):
                            is_intrusion_alarm = True
                            break
            
            # 2. Xử lý nháy còi báo động tùy theo mức độ ưu tiên
            if is_fire:
                SystemStatus.buzzer_active = True
                # Báo cháy: Nháy cực nhanh (0.1s)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.1)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.1)
            elif is_gas:
                SystemStatus.buzzer_active = True
                # Rò rỉ khí ga: Nháy vừa (0.3s)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.3)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.3)
            elif is_intrusion_alarm:
                SystemStatus.buzzer_active = True
                # Báo động xâm nhập khóa nhà: Nháy chậm (0.8s)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.8)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.8)
            elif is_mock:
                SystemStatus.buzzer_active = True
                # Giả lập: Nháy chu kỳ 0.5s
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.5)
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.5)
            else:
                if SystemStatus.buzzer_active:
                    SystemStatus.buzzer_active = False
                if has_gpio:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[BUZZER] Lỗi vòng lặp điều khiển: {e}")
            time.sleep(2.0)

# =========================================================================
# PHÂN HỆ ĐIỀU KHIỂN ĐÈN CHIẾU SÁNG THÔNG MINH (LIGHT RELAY VIA GPIO 22)
# =========================================================================
auto_light_timer = None
auto_light_lock = threading.Lock()

def set_light_state(state: bool):
    """Đặt trạng thái bật/tắt rơ-le đèn chiếu sáng (GPIO 22)"""
    SystemStatus.light_active = state
    
    has_gpio = False
    try:
        import RPi.GPIO as GPIO
        has_gpio = True
    except ImportError:
        pass
        
    LIGHT_PIN = 22 # GPIO 22 (Pin 15)
    
    if has_gpio:
        try:
            orig_mode = GPIO.getmode()
            if orig_mode is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setup(LIGHT_PIN, GPIO.OUT)
            # Kích hoạt rơ-le đèn (HIGH = Bật, LOW = Tắt)
            GPIO.output(LIGHT_PIN, GPIO.HIGH if state else GPIO.LOW)
            print(f"[LIGHT RELAY] GPIO {LIGHT_PIN} set to {'HIGH' if state else 'LOW'}.")
        except Exception as e:
            print(f"[LIGHT RELAY] [ERROR] Lỗi điều khiển GPIO rơ-le đèn: {e}")
    else:
        print(f"[LIGHT RELAY] [SIMULATION] Rơ-le đèn đã được {'BẬT' if state else 'TẮT'} (Giả lập).")
    
    # Thêm log vào hệ thống
    state_str = "BẬT" if state else "TẮT"
    log_type = "success" if state else "muted"
    SystemStatus.add_log(f"💡 HỆ THỐNG: Đèn chiếu sáng thông minh đã được {state_str}.", log_type)

def get_frame_brightness(frame):
    """Tính toán độ sáng trung bình của khung hình (0-255)"""
    try:
        import cv2
        import numpy as np
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))
    except Exception as e:
        print(f"[LIGHT RELAY] Lỗi tính độ sáng khung hình: {e}")
        return 127.0

def trigger_auto_light(duration=30, frame=None):
    """Tự động bật đèn trong một khoảng thời gian (duration) rồi tắt."""
    global auto_light_timer
    
    # Đọc cấu hình chế độ hoạt động
    from app.config import settings
    mode = settings.get("light_trigger_mode", "always")
    
    # 1. Kiểm tra khung giờ hoạt động
    if mode in ("schedule", "both"):
        try:
            from datetime import datetime, time
            now_time = datetime.now().time()
            start_str = settings.get("light_schedule_start", "18:00")
            end_str = settings.get("light_schedule_end", "06:00")
            
            sh, sm = map(int, start_str.split(":"))
            start_t = time(sh, sm)
            
            eh, em = map(int, end_str.split(":"))
            end_t = time(eh, em)
            
            in_range = False
            if start_t <= end_t:
                in_range = (start_t <= now_time <= end_t)
            else:
                in_range = (now_time >= start_t or now_time <= end_t)
                
            if not in_range:
                print(f"[LIGHT RELAY] Tự động bật đèn bị bỏ qua: Ngoài khung giờ cấu hình ({start_str} - {end_str}). Hiện tại: {now_time.strftime('%H:%M:%S')}")
                return
        except Exception as err:
            print(f"[LIGHT RELAY] Lỗi kiểm tra khung giờ: {err}")
            
    # 2. Kiểm tra độ sáng khung hình (Trời tối)
    if mode in ("dark", "both"):
        if frame is not None:
            brightness = get_frame_brightness(frame)
            threshold = settings.get("light_brightness_threshold", 60)
            if brightness >= threshold:
                print(f"[LIGHT RELAY] Tự động bật đèn bị bỏ qua: Khung hình đủ sáng ({brightness:.1f} >= ngưỡng {threshold}).")
                return
            else:
                print(f"[LIGHT RELAY] Phát hiện trời tối: Độ sáng khung hình {brightness:.1f} < ngưỡng {threshold}.")
        else:
            print(f"[LIGHT RELAY] Bỏ qua kiểm tra độ sáng vì không có khung hình sự cố.")
            
    with auto_light_lock:
        # Bật đèn nếu chưa bật
        if not SystemStatus.light_active:
            set_light_state(True)
        
        # Hủy timer cũ nếu có
        if auto_light_timer is not None:
            auto_light_timer.cancel()
            
        # Tạo timer mới tắt đèn sau `duration` giây
        auto_light_timer = threading.Timer(duration, _auto_light_off_worker)
        auto_light_timer.start()
        print(f"[LIGHT RELAY] Tự động bật đèn trong {duration} giây...")

def _auto_light_off_worker():
    global auto_light_timer
    with auto_light_lock:
        set_light_state(False)
        auto_light_timer = None
