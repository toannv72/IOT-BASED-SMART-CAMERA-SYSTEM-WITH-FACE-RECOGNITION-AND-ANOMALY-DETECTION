import cv2
import requests
import torch
import numpy as np
import time
import json
import os
from ultralytics import YOLO
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image

# --- CẤU HÌNH HỆ THỐNG EDGE ---
API_URL_EMBEDDINGS = "http://localhost:8000/embeddings"
TELEGRAM_TOKEN = "8788292129:AAG-BKlK_c9YbdArYQ4QoqyKZBD-29esw50"  # Điền Token của bạn
# Đổi thành danh sách để gửi cho nhiều người
TELEGRAM_CHAT_IDS = [
    "8438973190", 
    # "ID_CUA_NGUOI_THU_2", # Bỏ comment và thay số ID người khác vào đây
    # "ID_CUA_NGUOI_THU_3"
]  
COOLDOWN_SECONDS = 30
THRESHOLD = 0.8 # Độ khắt khe khi nhận diện khuôn mặt
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "cameras_config.json")

# Biến toàn cục
last_alert_time = 0

def send_telegram_alert(message, frame):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time < COOLDOWN_SECONDS:
        return 
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success: return
        
        # Gửi cho tất cả ID trong danh sách
        for chat_id in TELEGRAM_CHAT_IDS:
            # Lưu ý: phải tạo lại biến files trong mỗi vòng lặp
            files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
            payload = {"chat_id": chat_id, "caption": message}
            requests.post(url, data=payload, files=files, timeout=10)
            
        last_alert_time = current_time
        print(">>> [ANOMALY DETECTED] Đã gửi cảnh báo Telegram đến tất cả tài khoản!")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def load_registered_faces():
    print("Đang đồng bộ Cơ sở dữ liệu từ Backend API...")
    try:
        response = requests.get(API_URL_EMBEDDINGS)
        if response.status_code == 200:
            data = response.json()
            if not data: return [], []
            names = [p["name"] for p in data]
            embeddings = [p["embedding"] for p in data]
            return names, np.array(embeddings)
        return [], []
    except Exception as e:
        print("LỖI: Không thể kết nối tới Backend API (face_api.py).")
        return [], []

def main():
    # 1. Khởi tạo Models
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Khởi tạo AI Models trên {device}...")
    
    # YOLOv8 cho Phát hiện & Theo dõi hành vi (Anomaly / Person Tracking)
    yolo_model = YOLO("yolov8n.pt") 
    
    # FaceNet cho Nhận diện khuôn mặt
    mtcnn = MTCNN(keep_all=True, device=device)
    resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    # 2. Tải dữ liệu
    names, db_embeddings = load_registered_faces()

    # 3. Mở Camera
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)[0] # Lấy camera đầu tiên làm ví dụ
        
    source = config["source"]
    source = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print("Không thể mở Camera!")
        return

    print("\n--- HỆ THỐNG EDGE NODE SẴN SÀNG ---")
    print("Nhấn 'q' để thoát, 'r' để đồng bộ lại dữ liệu.")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        display_frame = frame.copy()
        
        # Bước 1: YOLOv8 Quét toàn cảnh (Chỉ tìm Người)
        results = yolo_model.track(frame, persist=True, classes=[0], verbose=False)
        person_boxes = []
        if results[0].boxes.id is not None:
            person_boxes = results[0].boxes.xyxy.cpu().numpy()

        # Vẽ khung người (Bounding box tổng)
        for pbox in person_boxes:
            px1, py1, px2, py2 = [int(p) for p in pbox]
            cv2.rectangle(display_frame, (px1, py1), (px2, py2), (255, 255, 0), 1)
        
        # Bước 2: FaceNet Tìm và Nhận diện khuôn mặt
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        face_boxes, _ = mtcnn.detect(img_pil)
        
        if face_boxes is not None:
            faces = mtcnn(img_pil)
            if faces is not None:
                embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                
                for i, (box, emb) in enumerate(zip(face_boxes, embeddings)):
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
                                
                    # Bước 3: Logic Phân Tích Hành Vi (Anomaly Detection)
                    if best_match_name == "Unknown":
                        color = (0, 0, 255) # Đỏ cảnh báo
                        # Gửi Telegram nếu có người lạ lọt vào khung hình
                        send_telegram_alert("⚠️ ANOMALY DETECTED: Phát hiện người lạ xâm nhập!", frame)
                    else:
                        color = (0, 255, 0) # Xanh an toàn
                        
                    # Vẽ khung mặt
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                    cv2.putText(display_frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Edge Node (YOLOv8 + FaceNet)", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('r'):
            names, db_embeddings = load_registered_faces()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
