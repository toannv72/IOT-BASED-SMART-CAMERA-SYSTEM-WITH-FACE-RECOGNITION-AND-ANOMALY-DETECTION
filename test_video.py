import torch
import cv2
import numpy as np
import requests
import json
import time
import os

# --- CÀI ĐẶT ---
# Thay đổi Token và Chat ID của bạn ở đây
TELEGRAM_TOKEN = "8788292129:AAG-BKlK_c9YbdArYQ4QoqyKZBD-29esw50"
TELEGRAM_CHAT_ID = "8438973190"
COOLDOWN_SECONDS = 10  # Thời gian chờ giữa các lần gửi cảnh báo (test video để ngắn hơn)

# Đường dẫn file video của bạn (THAY ĐỔI ĐƯỜNG DẪN TẠI ĐÂY)
video_path = "video1.mp4" 

ROI_FILE = "roi_video.json" # Lưu vùng ROI riêng cho video
# ---------------

# Tải vùng ROI từ file nếu có
points = []
if os.path.exists(ROI_FILE):
    try:
        with open(ROI_FILE, "r") as f:
            points = json.load(f)
    except:
        points = []

last_alert_time = 0

def send_telegram_alert(message, frame):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time < COOLDOWN_SECONDS:
        return 
    
    # Sử dụng endpoint sendPhoto của Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    try:
        # Mã hóa frame thành định dạng JPEG trong bộ nhớ
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            return

        # Chuẩn bị file và nội dung
        files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": message}
        
        requests.post(url, data=payload, files=files, timeout=10)
        last_alert_time = current_time
        print("Đã gửi hình ảnh cảnh báo Telegram!")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def handle_mouse(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        with open(ROI_FILE, "w") as f:
            json.dump(points, f)
    elif event == cv2.EVENT_RBUTTONDOWN:
        points = []
        if os.path.exists(ROI_FILE):
            os.remove(ROI_FILE)

# Load model YOLOv5
print("Đang tải model YOLOv5...")
model = torch.hub.load("ultralytics/yolov5", "yolov5s")
model.classes = [0] 
model.conf = 0.3 # Tăng độ nhạy (ngưỡng 0.3)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(f"LỖI: Không thể mở video tại đường dẫn: {video_path}")
    print("Vui lòng kiểm tra lại tên file và đường dẫn.")
    exit()

window_name = 'TEST VIDEO - Click chuot trai de ve ROI, phai de xoa'
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, handle_mouse)

print(f"Đang chạy video: {video_path}")
print("Phím 'q': Thoát")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Đã kết thúc video hoặc không đọc được frame.")
        break

    # Tùy chỉnh kích thước hiển thị nếu cần (ví dụ: 960x540)
    # frame = cv2.resize(frame, (960, 540))

    # Dự đoán
    results = model(frame)
    detections = results.xyxy[0].cpu().numpy() 
    
    person_in_roi = False
    
    # Vẽ vùng ROI hiện tại
    if len(points) > 1:
        pts = np.array(points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
    
    for det in detections:
        x1, y1, x2, y2, conf, cls = det
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        # Danh sách 6 điểm kiểm tra (4 góc, tâm, bàn chân)
        check_points = [
            (x1, y1), (x2, y1), (x1, y2), (x2, y2),
            (int((x1 + x2) / 2), int((y1 + y2) / 2)),
            (int((x1 + x2) / 2), y2)
        ]
        
        is_in_this_det = False
        if len(points) > 2:
            for cp in check_points:
                if cv2.pointPolygonTest(np.array(points, np.int32), cp, False) >= 0:
                    is_in_this_det = True
                    break
            
            if is_in_this_det:
                person_in_roi = True
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                for cp in check_points:
                    cv2.circle(frame, cp, 3, (0, 0, 255), -1)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
        cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if person_in_roi:
        cv2.putText(frame, "CANH BAO: CO NGUOI XAM NHAP!", (10, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        send_telegram_alert(f"⚠️ Test Video: Phát hiện xâm nhập!", frame)
    else:
        cv2.putText(frame, "Trang thai: Binh thuong", (10, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow(window_name, frame)

    # Chỉnh tốc độ video tại cv2.waitKey (ví dụ 30ms cho video 30fps)
    if cv2.waitKey(30) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
