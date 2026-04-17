import torch
import cv2
import numpy as np
import requests
import json
import time
import os
from collections import deque
from datetime import datetime

# --- SETTINGS ---
TELEGRAM_TOKEN = "8788292129:AAG-BKlK_c9YbdArYQ4QoqyKZBD-29esw50"
TELEGRAM_CHAT_ID = "8438973190"
COOLDOWN_SECONDS = 3  # Đợi 1 phút giữa các lần gửi cảnh báo

INPUT_DIR = "input_videos"
OUTPUT_DIR = "output_events"
# ----------------

# Tạo các thư mục cần thiết
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load model YOLOv5
print("Đang tải model YOLOv5...")
model = torch.hub.load("ultralytics/yolov5", "yolov5s")
model.classes = [0] # Chỉ phát hiện người
model.conf = 0.4    # Ngưỡng tin cậy

def send_telegram_alert(message, frame):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success: return
        files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": message}
        requests.post(url, data=payload, files=files, timeout=10)
        print(">>> Đã gửi ảnh cảnh báo lên Telegram!")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def get_roi(video_path, filename):
    roi_file = f"roi_{filename}.json"
    points = []
    
    if os.path.exists(roi_file):
        with open(roi_file, "r") as f:
            points = json.load(f)
        return points

    # Nếu chưa có, yêu cầu vẽ
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if not ret: return []
    
    temp_points = []
    def handle_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            temp_points.append([x, y])
            cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)
            if len(temp_points) > 1:
                cv2.line(frame, tuple(temp_points[-2]), tuple(temp_points[-1]), (0, 255, 255), 2)
            cv2.imshow("VE VUNG ROI - Click chuot trai de ve, cam phim bat ky de LUu", frame)

    cv2.imshow("VE VUNG ROI - Click chuot trai de ve, cam phim bat ky de LUu", frame)
    cv2.setMouseCallback("VE VUNG ROI - Click chuot trai de ve, cam phim bat ky de LUu", handle_mouse)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    if len(temp_points) > 2:
        with open(roi_file, "w") as f:
            json.dump(temp_points, f)
    cap.release()
    return temp_points

def process_video(video_path):
    filename = os.path.basename(video_path)
    print(f"\n--- Dang xu ly: {filename} ---")
    
    pts_roi = get_roi(video_path, filename)
    if not pts_roi:
        print(f"Bo qua {filename} vi khong co vung ROI.")
        return

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 1 phút bộ đệm (1 min = 60s)
    buffer_len = fps * 60
    pre_buffer = deque(maxlen=buffer_len)
    
    is_recording = False
    out_writer = None
    last_detect_time = 0
    post_buffer_frames = fps * 60 # 1 phút ghi sau sự kiện
    frames_since_last_detect = 0
    
    last_telegram_time = 0

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Vẽ timestamp (giả lập thời gian thực dựa trên frame count)
        processed_frame = frame.copy()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, timestamp, (10, height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Vẽ ROI
        cv2.polylines(processed_frame, [np.array(pts_roi, np.int32)], True, (0, 255, 255), 2)

        # Nhận diện người
        results = model(frame)
        detections = results.xyxy[0].cpu().numpy()
        
        detected_in_roi = False
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            points_to_check = [
                (int((x1+x2)/2), int(y2)), # Foot
                (int((x1+x2)/2), int((y1+y2)/2)), # Center
                (int(x1), int(y1)), (int(x2), int(y2)) # Corners
            ]
            
            in_this = False
            for p in points_to_check:
                if cv2.pointPolygonTest(np.array(pts_roi, np.int32), p, False) >= 0:
                    in_this = True
                    break
            
            if in_this:
                detected_in_roi = True
                cv2.rectangle(processed_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
            else:
                cv2.rectangle(processed_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        # Logic ghi hình
        if detected_in_roi:
            frames_since_last_detect = 0
            if not is_recording:
                # Bắt đầu ghi file mới
                out_name = f"event_{int(time.time())}_{filename}"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out_writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
                
                # Xả bộ đệm 1 phút trước đó vào file
                print(f"!!! PHAT HIEN NGUOI !!! Bat dau ghi hinh: {out_name}")
                while pre_buffer:
                    out_writer.write(pre_buffer.popleft())
                is_recording = True
                
                # Gửi Telegram ngay lập tức (kèm cooldown)
                current_t = time.time()
                if current_t - last_telegram_time > COOLDOWN_SECONDS:
                    send_telegram_alert(f"⚠️ CANH BAO: Phat hien xam nhap trong video {filename}!", processed_frame)
                    last_telegram_time = current_t
        else:
            if is_recording:
                frames_since_last_detect += 1
                if frames_since_last_detect > post_buffer_frames:
                    print(f"Xong sự kiện. Da luu file.")
                    is_recording = False
                    out_writer.release()
                    out_writer = None

        if is_recording:
            out_writer.write(processed_frame)
        else:
            # Chỉ lưu vào bộ đệm khi KHÔNG đang ghi hình trực tiếp
            pre_buffer.append(processed_frame)

        # Hiển thị preview (tùy chọn, có thể giảm tốc độ xử lý)
        cv2.imshow("DANG XU LY BATCH - Nhan 'q' de bo qua video", processed_frame)
        if cv2.waitKey(1) == ord('q'):
            break

    if out_writer:
        out_writer.release()
    cap.release()
    cv2.destroyAllWindows()

# Main Loop
video_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(('.mp4', '.avi', '.mkv'))]
if not video_files:
    print(f"Khong tim thay file video nao trong thu muc {INPUT_DIR}")
else:
    for vid in video_files:
        full_path = os.path.join(INPUT_DIR, vid)
        process_video(full_path)
    print("\n--- HOAN THANH TOAN BO ---")
