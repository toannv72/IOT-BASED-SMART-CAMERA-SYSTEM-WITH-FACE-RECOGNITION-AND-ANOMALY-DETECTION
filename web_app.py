import os
import json
import time
import torch
import cv2
import numpy as np
import io
import threading
import webbrowser
from collections import deque
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from facenet_pytorch import MTCNN, InceptionResnetV1
from ultralytics import YOLO
from PIL import Image
import requests
import supervision as sv

# --- CẤU HÌNH HỆ THỐNG MẶC ĐỊNH ---
SETTINGS_FILE = "settings.json"
DEFAULT_TELEGRAM_TOKEN = "8788292129:AAG-BKlK_c9YbdArYQ4QoqyKZBD-29esw50"
DEFAULT_TELEGRAM_CHATS = ["8438973190"]

# Tải cấu hình
settings = {
    "telegram_token": DEFAULT_TELEGRAM_TOKEN,
    "telegram_chats": DEFAULT_TELEGRAM_CHATS
}
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings.update(json.load(f))
    except Exception:
        pass

def save_settings():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Lỗi lưu file cấu hình: {e}")

# --- Khởi tạo Database ---
DATABASE_URL = "sqlite:///faces.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FaceRecord(Base):
    __tablename__ = "faces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    embedding = Column(Text)

Base.metadata.create_all(bind=engine)

# --- KHỞI TẠO AI MODELS ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"==================================================")
print(f"[SYSTEM] Đang khởi chạy AI Models trên thiết bị: {device}")
print(f"==================================================")

# 1. FaceNet Models
mtcnn_single = MTCNN(keep_all=False, device=device) # Cho đăng ký
mtcnn_multi = MTCNN(keep_all=True, device=device)   # Cho nhận diện trực tiếp
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# 2. YOLOv5 cho ROI Intrusion
print("[SYSTEM] Đang tải YOLOv5...")
yolov5_model = torch.hub.load("ultralytics/yolov5", "yolov5s").to(device)
yolov5_model.classes = [0] # Chỉ người
yolov5_model.conf = 0.4

# 3. YOLOv8 cho Counter
print("[SYSTEM] Đang tải YOLOv8 (yolov8s.pt)...")
yolov8_model = YOLO("yolov8s.pt")
yolov8_model.to(device)

# 4. YOLOv8-pose cho Fall Detection
print("[SYSTEM] Đang tải YOLOv8-pose...")
yolov8_pose_model = YOLO("yolov8n-pose.pt")
yolov8_pose_model.to(device)

# 4b. YOLOv8-fall cho Fall Detection (Mô hình tự train)
yolov8_fall_model_path = "yolov8n_fall_best.pt"
yolov8_fall_model = None
if os.path.exists(yolov8_fall_model_path):
    print(f"[SYSTEM] Phát hiện mô hình ngã tự train: {yolov8_fall_model_path}. Đang tải...")
    try:
        yolov8_fall_model = YOLO(yolov8_fall_model_path)
        yolov8_fall_model.to(device)
        print("[SYSTEM] Đã tải mô hình YOLOv8-fall tự train thành công!")
    except Exception as e:
        print(f"[ERROR] Không thể tải mô hình YOLOv8-fall tự train: {e}")

# --- TRẠNG THÁI HỆ THỐNG TOÀN CỤC ---
class SystemStatus:
    intrusion_active = False
    fall_active = False
    new_logs = []
    log_lock = threading.Lock()
    
    @classmethod
    def add_log(cls, msg, log_type=""):
        with cls.log_lock:
            cls.new_logs.append({
                "msg": msg,
                "type": log_type,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            if len(cls.new_logs) > 50:
                cls.new_logs.pop(0)

# Cảnh báo Telegram
last_alert_time = 0
last_fall_alert_time = 0
COOLDOWN_SECONDS = 15

def send_telegram_alert(message, frame, alert_type="intrusion"):
    global last_alert_time, last_fall_alert_time
    current_time = time.time()
    if alert_type == "intrusion":
        if current_time - last_alert_time < COOLDOWN_SECONDS:
            return 
        last_alert_time = current_time
    else:
        if current_time - last_fall_alert_time < COOLDOWN_SECONDS:
            return 
        last_fall_alert_time = current_time
    
    # Sao chép frame để tránh xung đột đa luồng khi thread chạy nền
    frame_copy = frame.copy()
    
    def send_worker():
        url = f"https://api.telegram.org/bot{settings['telegram_token']}/sendPhoto"
        try:
            success, buffer = cv2.imencode(".jpg", frame_copy)
            if not success: return
            
            for chat_id in settings["telegram_chats"]:
                files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
                payload = {"chat_id": chat_id, "caption": message}
                requests.post(url, data=payload, files=files, timeout=10)
                
            print(f"[TELEGRAM] Đã gửi hình ảnh cảnh báo {alert_type} thành công (chạy nền)!")
        except Exception as e:
            print(f"[TELEGRAM] Lỗi gửi tin nhắn {alert_type}: {e}")

    threading.Thread(target=send_worker, daemon=True).start()

# --- KHỞI TẠO FASTAPI APP ---
app = FastAPI(title="Unified Smart Surveillance Dashboard")

class SettingsPayload(BaseModel):
    telegram_token: str
    telegram_chats: list

# --- ENDPOINTS HỆ THỐNG ---
@app.get("/")
def read_root():
    # Phục vụ tệp HTML
    html_path = os.path.join("templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Templates folder or index.html not found!</h1>")

@app.get("/gpu_info")
def get_gpu_info():
    return {
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_active": torch.cuda.is_available()
    }

@app.get("/system_status")
def get_system_status():
    with SystemStatus.log_lock:
        logs_to_return = list(SystemStatus.new_logs)
        SystemStatus.new_logs.clear() # Lấy xong xóa đi để tránh trả trùng
    
    return {
        "intrusion_alert": SystemStatus.intrusion_active,
        "fall_alert": SystemStatus.fall_active,
        "new_logs": logs_to_return
    }

@app.get("/settings")
def get_settings():
    return {
        "telegram_token": settings["telegram_token"],
        "telegram_chats": settings["telegram_chats"]
    }

@app.post("/settings")
def update_settings(payload: SettingsPayload):
    settings["telegram_token"] = payload.telegram_token
    settings["telegram_chats"] = payload.telegram_chats
    save_settings()
    SystemStatus.add_log("Cấu hình Telegram đã được cập nhật.", "success")
    return {"message": "Đã cập nhật cấu hình!"}

# --- ENDPOINTS FACE DATABASE (Giữ nguyên cấu trúc của face_api.py để tương thích hoàn toàn) ---
def get_embedding(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    face = mtcnn_single(img)
    if face is None:
        return None
    face = face.unsqueeze(0).to(device)
    embedding = resnet(face).detach().cpu().numpy()[0]
    return embedding

@app.post("/register")
async def register_face(name: str = Form(...), file: UploadFile = File(...)):
    image_bytes = await file.read()
    embedding = get_embedding(image_bytes)
    
    if embedding is None:
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt nào trong ảnh!")
    
    emb_list = embedding.tolist()
    emb_json = json.dumps(emb_list)
    
    db = SessionLocal()
    new_face = FaceRecord(name=name, embedding=emb_json)
    db.add(new_face)
    db.commit()
    db.refresh(new_face)
    db.close()
    
    SystemStatus.add_log(f"Đã đăng ký thành công khuôn mặt mới: {name}", "success")
    return {"message": "Đăng ký thành công!", "id": new_face.id, "name": new_face.name}

@app.get("/faces")
def get_all_faces():
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    return [{"id": f.id, "name": f.name} for f in faces]

@app.get("/embeddings")
def get_embeddings():
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    
    result = []
    for f in faces:
        result.append({
            "id": f.id,
            "name": f.name,
            "embedding": json.loads(f.embedding)
        })
    return result

@app.delete("/faces/{face_id}")
def delete_face(face_id: int):
    db = SessionLocal()
    face = db.query(FaceRecord).filter(FaceRecord.id == face_id).first()
    if not face:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy khuôn mặt này.")
    
    name = face.name
    db.delete(face)
    db.commit()
    db.close()
    
    SystemStatus.add_log(f"Đã xóa khuôn mặt: {name} (ID: {face_id})", "danger")
    return {"message": "Đã xóa thành công!"}

# --- GENERATORS CHO VIDEO MJPEG STREAMING ---

# 1. Generator nhận diện khuôn mặt trực tiếp (Face Recognition)
def gen_face_stream():
    # Tải trước các embeddings đã đăng ký
    db = SessionLocal()
    records = db.query(FaceRecord).all()
    db.close()
    
    names = [r.name for r in records]
    db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Không thể mở webcam cho luồng khuôn mặt!")
        return

    THRESHOLD = 0.8
    print("[STREAM] Khởi tạo luồng nhận diện khuôn mặt từ Webcam 0...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        boxes, _ = mtcnn_multi.detect(img_pil)
        
        if boxes is not None:
            faces = mtcnn_multi(img_pil)
            if faces is not None:
                # Đưa lên CUDA để xử lý song song
                embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                
                for i, (box, emb) in enumerate(zip(boxes, embeddings)):
                    x1, y1, x2, y2 = [int(b) for b in box]
                    best_match_name = "Unknown"
                    best_distance = float("inf")
                    
                    if len(db_embeddings) > 0:
                        distances = np.linalg.norm(db_embeddings - emb, axis=1)
                        min_idx = np.argmin(distances)
                        min_dist = distances[min_idx]
                        
                        if min_dist < THRESHOLD:
                            best_match_name = names[min_idx]
                            best_distance = min_dist
                            
                    color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Nén thành file ảnh JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
    cap.release()

# 2. Generator giám sát xâm nhập vùng cấm ROI (YOLOv5)
def gen_roi_stream():
    video_path = "video1.mp4"
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Không thể mở video ROI: {video_path}")
        return

    # Tải vùng ROI từ file cấu hình
    ROI_FILE = "roi_video.json"
    points = []
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                points = json.load(f)
        except Exception:
            pass
            
    # Dự phòng nếu file ROI trống, vẽ vùng đa giác trung tâm mặc định
    if len(points) < 3:
        points = [[150, 150], [550, 150], [580, 450], [120, 450]]

    print("[STREAM] Khởi tạo luồng cảnh báo xâm nhập ROI...")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Lặp lại video liên tục để test
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        results = yolov5_model(frame)
        detections = results.xyxy[0].cpu().numpy()
        
        person_in_roi = False
        
        # Vẽ đa giác ROI (vàng)
        pts = np.array(points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
        
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Điểm chân và tâm của người
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
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
            cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        if person_in_roi:
            SystemStatus.intrusion_active = True
            cv2.putText(frame, "CANH BAO: XAM NHAP!", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người lạ xâm nhập vùng cấm!", "danger")
            # Gửi tin nhắn Telegram
            send_telegram_alert("⚠️ Web Dashboard: Phát hiện xâm nhập vùng cấm!", frame)
        else:
            SystemStatus.intrusion_active = False
            cv2.putText(frame, "Trang thai: Binh thuong", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
    cap.release()

# Helper kiểm tra giao cắt (Đếm người)
def check_intersect(A, B, C, D):
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

# 3. Generator đếm người qua vạch kẻ (YOLOv8 Multi-Camera)
def gen_counter_stream():
    CONFIG_FILE = "cameras_config.json"
    
    # Load camera configurations
    try:
        with open(CONFIG_FILE, "r") as f:
            cameras = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config in web app: {e}")
        # Default fallback configurations
        cameras = [
            {
                "camera_id": "Cam_Cua_Chinh",
                "source": "video.mp4",
                "line": [[154, 246], [437, 261]],
                "in_direction": "down"
            },
            {
                "camera_id": "Cam_Cua_Sau",
                "source": "video1.mp4",
                "line": [[0, 210], [579, 245]],
                "in_direction": "up"
            }
        ]
        
    cam1_cfg = next((c for c in cameras if c["camera_id"] == "Cam_Cua_Chinh"), cameras[0])
    cam2_cfg = next((c for c in cameras if c["camera_id"] == "Cam_Cua_Sau"), cameras[1])
    
    cap1 = cv2.VideoCapture(cam1_cfg["source"])
    cap2 = cv2.VideoCapture(cam2_cfg["source"])
    
    # Helper to build double lines info
    import math
    
    def get_cam_double_lines(cfg):
        x1, y1 = cfg["line"][0]
        x2, y2 = cfg["line"][1]
        
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: length = 1.0
        
        nx = -dy / length
        ny = dx / length
        d = 30.0
        
        in_dir = cfg.get("in_direction", "down")
        if in_dir == "down":
            dot = ny
        elif in_dir == "up":
            dot = -ny
        elif in_dir == "right":
            dot = nx
        elif in_dir == "left":
            dot = -nx
        else:
            dot = 1.0
            
        if dot >= 0:
            outside_reg = 1
            inside_reg = 3
            line_outer_A = (int(x1 - d * nx), int(y1 - d * ny))
            line_outer_B = (int(x2 - d * nx), int(y2 - d * ny))
            line_inner_A = (int(x1 + d * nx), int(y1 + d * ny))
            line_inner_B = (int(x2 + d * nx), int(y2 + d * ny))
        else:
            outside_reg = 3
            inside_reg = 1
            line_outer_A = (int(x1 + d * nx), int(y1 + d * ny))
            line_outer_B = (int(x2 + d * nx), int(y2 + d * ny))
            line_inner_A = (int(x1 - d * nx), int(y1 - d * ny))
            line_inner_B = (int(x2 - d * nx), int(y2 - d * ny))
            
        return nx, ny, outside_reg, inside_reg, line_outer_A, line_outer_B, line_inner_A, line_inner_B

    # Initialize double-line setup for both cameras
    nx_1, ny_1, outside_reg_1, inside_reg_1, l_out_A_1, l_out_B_1, l_in_A_1, l_in_B_1 = get_cam_double_lines(cam1_cfg)
    nx_2, ny_2, outside_reg_2, inside_reg_2, l_out_A_2, l_out_B_2, l_in_A_2, l_in_B_2 = get_cam_double_lines(cam2_cfg)
    
    # Counts
    count_in_1, count_out_1 = 0, 0
    count_in_2, count_out_2 = 0, 0
    
    # Cam 1 states
    track_states1 = {}   # tid -> 'from_outside' | 'from_inside'
    lost_tracks1 = {}    # tid -> (state, last_pos, frame_index)
    active_tracks1 = {}  # tid -> bottom_center
    frame_index1 = 0
    
    # Cam 2 states
    track_states2 = {}   # tid -> 'from_outside' | 'from_inside'
    lost_tracks2 = {}    # tid -> (state, last_pos, frame_index)
    active_tracks2 = {}  # tid -> bottom_center
    frame_index2 = 0
    
    # Annotators from supervision
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    
    print("[STREAM] Khởi tạo luồng ghép đôi đếm người đa kênh (Supervision & Double-Line)...")
    
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not ret1 or not ret2:
            # Re-read config dynamically so lines updated in GUI are updated here too!
            try:
                with open(CONFIG_FILE, "r") as f:
                    new_cams = json.load(f)
                cam1_cfg = next((c for c in new_cams if c["camera_id"] == "Cam_Cua_Chinh"), cam1_cfg)
                cam2_cfg = next((c for c in new_cams if c["camera_id"] == "Cam_Cua_Sau"), cam2_cfg)
            except Exception:
                pass
                
            if not ret1:
                cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
                nx_1, ny_1, outside_reg_1, inside_reg_1, l_out_A_1, l_out_B_1, l_in_A_1, l_in_B_1 = get_cam_double_lines(cam1_cfg)
                track_states1.clear()
                lost_tracks1.clear()
                active_tracks1.clear()
                frame_index1 = 0
            if not ret2:
                cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
                nx_2, ny_2, outside_reg_2, inside_reg_2, l_out_A_2, l_out_B_2, l_in_A_2, l_in_B_2 = get_cam_double_lines(cam2_cfg)
                track_states2.clear()
                lost_tracks2.clear()
                active_tracks2.clear()
                frame_index2 = 0
            continue

        # --- XỬ LÝ CAMERA 1 ---
        frame_index1 += 1
        results1 = yolov8_model.track(frame1, persist=True, tracker="custom_bytetrack.yaml", conf=0.25, classes=[0], verbose=False, device=device)
        detections1 = sv.Detections.from_ultralytics(results1[0])
        detections1 = detections1[detections1.class_id == 0]
        
        diff_in_1 = 0
        diff_out_1 = 0
        
        x1_1, y1_1 = cam1_cfg["line"][0]
        d = 30.0
        
        current_active_tids1 = set()
        
        if detections1.tracker_id is not None and len(detections1.tracker_id) == len(detections1):
            for i, tid in enumerate(detections1.tracker_id):
                current_active_tids1.add(tid)
                bbox = detections1.xyxy[i]
                curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                
                # 1. Lost track state inheritance
                if tid not in track_states1:
                    best_match_tid = None
                    best_match_dist = float('inf')
                    bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                    for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(lost_tracks1.items()):
                        if lost_tid != tid and frame_index1 - lost_frame < 45:
                            dist = math.dist(curr_bc, lost_pos)
                            max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (frame_index1 - lost_frame))
                            if dist < max_dist and dist < best_match_dist:
                                best_match_tid = lost_tid
                                best_match_dist = dist
                    if best_match_tid is not None:
                        lost_state_tuple, _, _ = lost_tracks1[best_match_tid]
                        if lost_state_tuple is not None:
                            track_states1[tid] = lost_state_tuple
                            print(f"[CAM 1] [TRACK INHERIT] ID #{tid} inherited state {lost_state_tuple} from lost ID #{best_match_tid} (dist: {best_match_dist:.1f}px)")
                        if best_match_tid in lost_tracks1:
                            del lost_tracks1[best_match_tid]
                        if best_match_tid in track_states1:
                            del track_states1[best_match_tid]
                        
                active_tracks1[tid] = curr_bc
                if tid in lost_tracks1:
                    del lost_tracks1[tid]
                
                # 2. Projection & Region check
                x, y = curr_bc
                v = (x - x1_1) * nx_1 + (y - y1_1) * ny_1
                
                if v < -d:
                    region = 1
                elif v > d:
                    region = 3
                else:
                    region = 2
                    
                # 3. State machine with Cooldown
                state_tuple = track_states1.get(tid)
                if state_tuple is not None:
                    state, last_cross = state_tuple
                else:
                    state, last_cross = None, 0
                    
                if region == outside_reg_1:
                    if state == 'from_inside':
                        if frame_index1 - last_cross > 45:
                            diff_out_1 += 1
                            track_states1[tid] = ('from_outside', frame_index1)
                            print(f"[CAM 1] ID #{tid} completed crossing: INSIDE -> OUTSIDE. Counted OUT.")
                    else:
                        track_states1[tid] = ('from_outside', last_cross)
                elif region == inside_reg_1:
                    if state == 'from_outside':
                        if frame_index1 - last_cross > 45:
                            diff_in_1 += 1
                            track_states1[tid] = ('from_inside', frame_index1)
                            print(f"[CAM 1] ID #{tid} completed crossing: OUTSIDE -> INSIDE. Counted IN.")
                    else:
                        track_states1[tid] = ('from_inside', last_cross)
                    
        # 4. Clean up active tracks & update lost tracks (DO NOT delete from track_states1 immediately)
        for tid in list(active_tracks1.keys()):
            if tid not in current_active_tids1:
                last_pos = active_tracks1[tid]
                state_tuple = track_states1.get(tid)
                if state_tuple is not None:
                    lost_tracks1[tid] = (state_tuple, last_pos, frame_index1)
                del active_tracks1[tid]
                    
        # 5. Clean up stale lost tracks and track states to avoid memory leaks
        for tid in list(track_states1.keys()):
            if tid not in current_active_tids1:
                if tid in lost_tracks1:
                    state_tuple, pos, lost_frame = lost_tracks1[tid]
                    if frame_index1 - lost_frame > 150:
                        del track_states1[tid]
                        del lost_tracks1[tid]
                else:
                    del track_states1[tid]
                
        if diff_in_1 > 0 or diff_out_1 > 0:
            count_in_1 += diff_in_1
            count_out_1 += diff_out_1
            if diff_in_1 > 0:
                SystemStatus.add_log(f"📥 CAM 1: Có {diff_in_1} người đi VÀO cửa chính", "success")
            if diff_out_1 > 0:
                SystemStatus.add_log(f"📤 CAM 1: Có {diff_out_1} người đi RA cửa chính", "info")
        
        # --- XỬ LÝ CAMERA 2 ---
        frame_index2 += 1
        results2 = yolov8_model.track(frame2, persist=True, tracker="custom_bytetrack.yaml", conf=0.25, classes=[0], verbose=False, device=device)
        detections2 = sv.Detections.from_ultralytics(results2[0])
        detections2 = detections2[detections2.class_id == 0]
        
        diff_in_2 = 0
        diff_out_2 = 0
        
        x1_2, y1_2 = cam2_cfg["line"][0]
        
        current_active_tids2 = set()
        
        if detections2.tracker_id is not None and len(detections2.tracker_id) == len(detections2):
            for i, tid in enumerate(detections2.tracker_id):
                current_active_tids2.add(tid)
                bbox = detections2.xyxy[i]
                curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                
                # 1. Lost track state inheritance
                if tid not in track_states2:
                    best_match_tid = None
                    best_match_dist = float('inf')
                    bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                    for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(lost_tracks2.items()):
                        if lost_tid != tid and frame_index2 - lost_frame < 45:
                            dist = math.dist(curr_bc, lost_pos)
                            max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (frame_index2 - lost_frame))
                            if dist < max_dist and dist < best_match_dist:
                                best_match_tid = lost_tid
                                best_match_dist = dist
                    if best_match_tid is not None:
                        lost_state_tuple, _, _ = lost_tracks2[best_match_tid]
                        if lost_state_tuple is not None:
                            track_states2[tid] = lost_state_tuple
                            print(f"[CAM 2] [TRACK INHERIT] ID #{tid} inherited state {lost_state_tuple} from lost ID #{best_match_tid} (dist: {best_match_dist:.1f}px)")
                        if best_match_tid in lost_tracks2:
                            del lost_tracks2[best_match_tid]
                        if best_match_tid in track_states2:
                            del track_states2[best_match_tid]
                        
                active_tracks2[tid] = curr_bc
                if tid in lost_tracks2:
                    del lost_tracks2[tid]
                
                # 2. Projection & Region check
                x, y = curr_bc
                v = (x - x1_2) * nx_2 + (y - y1_2) * ny_2
                
                if v < -d:
                    region = 1
                elif v > d:
                    region = 3
                else:
                    region = 2
                    
                # 3. State machine with Cooldown
                state_tuple = track_states2.get(tid)
                if state_tuple is not None:
                    state, last_cross = state_tuple
                else:
                    state, last_cross = None, 0
                    
                if region == outside_reg_2:
                    if state == 'from_inside':
                        if frame_index2 - last_cross > 45:
                            diff_out_2 += 1
                            track_states2[tid] = ('from_outside', frame_index2)
                            print(f"[CAM 2] ID #{tid} completed crossing: INSIDE -> OUTSIDE. Counted OUT.")
                    else:
                        track_states2[tid] = ('from_outside', last_cross)
                elif region == inside_reg_2:
                    if state == 'from_outside':
                        if frame_index2 - last_cross > 45:
                            diff_in_2 += 1
                            track_states2[tid] = ('from_inside', frame_index2)
                            print(f"[CAM 2] ID #{tid} completed crossing: OUTSIDE -> INSIDE. Counted IN.")
                    else:
                        track_states2[tid] = ('from_inside', last_cross)
                    
        # 4. Clean up active tracks & update lost tracks (DO NOT delete from track_states2 immediately)
        for tid in list(active_tracks2.keys()):
            if tid not in current_active_tids2:
                last_pos = active_tracks2[tid]
                state_tuple = track_states2.get(tid)
                if state_tuple is not None:
                    lost_tracks2[tid] = (state_tuple, last_pos, frame_index2)
                del active_tracks2[tid]
                    
        # 5. Clean up stale lost tracks and track states to avoid memory leaks
        for tid in list(track_states2.keys()):
            if tid not in current_active_tids2:
                if tid in lost_tracks2:
                    state_tuple, pos, lost_frame = lost_tracks2[tid]
                    if frame_index2 - lost_frame > 150:
                        del track_states2[tid]
                        del lost_tracks2[tid]
                else:
                    del track_states2[tid]
                
        if diff_in_2 > 0 or diff_out_2 > 0:
            count_in_2 += diff_in_2
            count_out_2 += diff_out_2
            if diff_in_2 > 0:
                SystemStatus.add_log(f"📥 CAM 2: Có {diff_in_2} người đi VÀO lối đi sau", "success")
            if diff_out_2 > 0:
                SystemStatus.add_log(f"📤 CAM 2: Có {diff_out_2} người đi RA lối đi sau", "info")
 
        # --- VẼ UI VÀ GHÉP ẢNH ---
        # Cam 1 vẽ
        if detections1.tracker_id is not None and len(detections1.tracker_id) == len(detections1):
            labels1 = [f"#{tid}" for tid in detections1.tracker_id]
        else:
            labels1 = ["" for _ in range(len(detections1))]
        ann1 = frame1.copy()
        ann1 = box_annotator.annotate(scene=ann1, detections=detections1)
        ann1 = label_annotator.annotate(scene=ann1, detections=detections1, labels=labels1)
        
        cv2.line(ann1, l_out_A_1, l_out_B_1, (0, 165, 255), 2)  # Outer - Orange
        cv2.putText(ann1, "Vach Ngoai (OUTER)", (l_out_A_1[0], l_out_A_1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        cv2.line(ann1, l_in_A_1, l_in_B_1, (255, 100, 0), 2)  # Inner - Teal
        cv2.putText(ann1, "Vach Trong (INNER)", (l_in_A_1[0], l_in_A_1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)
        
        cv2.putText(ann1, f"CAM 1 (Cua Chinh) | IN: {count_in_1} | OUT: {count_out_1}", 
                    (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Cam 2 vẽ
        if detections2.tracker_id is not None and len(detections2.tracker_id) == len(detections2):
            labels2 = [f"#{tid}" for tid in detections2.tracker_id]
        else:
            labels2 = ["" for _ in range(len(detections2))]
        ann2 = frame2.copy()
        ann2 = box_annotator.annotate(scene=ann2, detections=detections2)
        ann2 = label_annotator.annotate(scene=ann2, detections=detections2, labels=labels2)
        
        cv2.line(ann2, l_out_A_2, l_out_B_2, (0, 165, 255), 2)  # Outer - Orange
        cv2.putText(ann2, "Vach Ngoai (OUTER)", (l_out_A_2[0], l_out_A_2[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        cv2.line(ann2, l_in_A_2, l_in_B_2, (255, 100, 0), 2)  # Inner - Teal
        cv2.putText(ann2, "Vach Trong (INNER)", (l_in_A_2[0], l_in_A_2[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)
        
        cv2.putText(ann2, f"CAM 2 (Cua Sau)  | IN: {count_in_2} | OUT: {count_out_2}", 
                    (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
 
        # Thu nhỏ để ghép đôi cạnh nhau
        ann1_res = cv2.resize(ann1, (480, 270))
        ann2_res = cv2.resize(ann2, (480, 270))
        
        # Ghép ngang (Horizontal stack)
        combined_frame = np.hstack((ann1_res, ann2_res))
        
        ret, buffer = cv2.imencode('.jpg', combined_frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
 
    cap1.release()
    cap2.release()

# 4. Generator phát hiện ngã bằng YOLOv8-pose
def gen_fall_stream():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Không thể mở webcam cho luồng phát hiện ngã! Sử dụng video.mp4 làm dự phòng.")
        cap = cv2.VideoCapture("video.mp4")
        if not cap.isOpened():
            print("[ERROR] Không thể mở video dự phòng!")
            return

    print("[STREAM] Khởi tạo luồng phát hiện ngã (YOLOv8-pose)...")
    fall_counter = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            # Nếu dùng file video thì loop lại
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            time.sleep(0.03) # Tránh loop quá nhanh gây quá tải CPU
            continue
            
        # Nhận diện ngã bằng mô hình YOLOv8-fall tự train (nếu có) hoặc fallback bằng YOLOv8-pose
        fall_in_frame = False
        
        if yolov8_fall_model is not None:
            results = yolov8_fall_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].cpu().item())
                    conf = float(box.conf[0].cpu().item())
                    
                    if conf > 0.4:
                        x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                        
                        if cls_id == 0:  # Fall (Class 0 mapped to fall)
                            color = (0, 0, 255)
                            label = f"FALL ({conf:.2f})"
                            fall_in_frame = True
                        else:  # Normal (Class 1 mapped to normal)
                            color = (0, 255, 0)
                            label = f"Normal ({conf:.2f})"
                            
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        else:
            # Fallback sang ước lượng tư thế bằng YOLOv8-pose
            results = yolov8_pose_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].keypoints is not None:
                keypoints_data = results[0].keypoints.data.cpu().numpy() # Shape: (N, 17, 3) hoặc (N, 17, 2)
                boxes = results[0].boxes.xyxy.cpu().numpy()
                
                for i, kpts in enumerate(keypoints_data):
                    box = boxes[i]
                    x1, y1, x2, y2 = [int(b) for b in box[:4]]
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    
                    # Trích xuất các điểm chính
                    # 0: nose, 5: l_shoulder, 6: r_shoulder, 11: l_hip, 12: r_hip, 15: l_ankle, 16: r_ankle
                    nose = kpts[0]
                    l_sho = kpts[5]
                    r_sho = kpts[6]
                    l_hip = kpts[11]
                    r_hip = kpts[12]
                    l_ank = kpts[15]
                    r_ank = kpts[16]
                    
                    has_conf = kpts.shape[1] == 3
                    
                    sho_x = (l_sho[0] + r_sho[0]) / 2
                    sho_y = (l_sho[1] + r_sho[1]) / 2
                    
                    hip_x = (l_hip[0] + r_hip[0]) / 2
                    hip_y = (l_hip[1] + r_hip[1]) / 2
                    
                    ank_x = (l_ank[0] + r_ank[0]) / 2
                    ank_y = (l_ank[1] + r_ank[1]) / 2
                    
                    is_horizontal = False
                    
                    sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                    hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0
                    ank_conf = min(l_ank[2], r_ank[2]) if has_conf else 1.0
                    
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        dy = sho_y - hip_y
                        dx = sho_x - hip_x
                        angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                        if angle_body < 40 or angle_body > 140:
                            is_horizontal = True
                    
                    if not is_horizontal and sho_conf > 0.3 and ank_conf > 0.3:
                        dy_full = ank_y - sho_y
                        dx_full = ank_x - sho_x
                        angle_full = abs(np.arctan2(dy_full, dx_full) * 180 / np.pi)
                        if angle_full < 40 or angle_full > 140:
                            is_horizontal = True
                    
                    if not is_horizontal and aspect_ratio > 1.3:
                        is_horizontal = True
                    
                    color = (0, 255, 0)
                    if is_horizontal:
                        color = (0, 0, 255)
                        fall_in_frame = True
                        
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"Ratio: {aspect_ratio:.2f}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        cv2.line(frame, (int(sho_x), int(sho_y)), (int(hip_x), int(hip_y)), (255, 255, 0), 2)
                    if hip_conf > 0.3 and ank_conf > 0.3:
                        cv2.line(frame, (int(hip_x), int(hip_y)), (int(ank_x), int(ank_y)), (255, 0, 255), 2)
                    
        if fall_in_frame:
            fall_counter += 1
            if fall_counter >= 12:  # Khoảng 1.2 giây
                SystemStatus.fall_active = True
                cv2.putText(frame, "CANH BAO: PHAT HIEN NGA!", (10, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người bị ngã hoặc nằm trên sàn!", "danger")
                send_telegram_alert("⚠️ Web Dashboard: Phát hiện người bị ngã hoặc nằm trên sàn!", frame, alert_type="fall")
        else:
            fall_counter = max(0, fall_counter - 1)
            if fall_counter == 0:
                SystemStatus.fall_active = False
                
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
    cap.release()

# --- STREAMING ROUTES ---
@app.get("/video_feed/face")
def video_feed_face():
    return StreamingResponse(gen_face_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/roi")
def video_feed_roi():
    return StreamingResponse(gen_roi_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/counter")
def video_feed_counter():
    return StreamingResponse(gen_counter_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/fall")
def video_feed_fall():
    return StreamingResponse(gen_fall_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

# --- HÀM TỰ ĐỘNG MỞ TRÌNH DUYỆT ---
def start_browser():
    # Đợi server lên khoảng 1.5 giây rồi mở browser
    time.sleep(1.5)
    print("[SYSTEM] Tự động mở trình duyệt Web Dashboard...")
    webbrowser.open("http://localhost:8000")

# --- CHẠY SERVER ---
if __name__ == "__main__":
    import uvicorn
    # Mở browser bằng một luồng riêng
    threading.Thread(target=start_browser, daemon=True).start()
    
    # Khởi động Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
