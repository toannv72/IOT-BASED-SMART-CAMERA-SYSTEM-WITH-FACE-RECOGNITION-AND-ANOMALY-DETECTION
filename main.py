import torch
import cv2
import numpy as np
import requests
import json
import time
import os

# --- CÀI ĐẶT ---
# Thay đổi Token và Chat ID của bạn ở đây
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
COOLDOWN_SECONDS = 30  # Thời gian chờ giữa các lần gửi cảnh báo (giây)

ROI_FILE = "roi.json"
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
        return # Đang trong thời gian chờ
    
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
        # Tự động lưu tọa độ
        with open(ROI_FILE, "w") as f:
            json.dump(points, f)
    elif event == cv2.EVENT_RBUTTONDOWN:
        points = []
        if os.path.exists(ROI_FILE):
            os.remove(ROI_FILE)

# Load model YOLOv5
model = torch.hub.load("ultralytics/yolov5", "yolov5s")
model.classes = [0] # Chỉ phát hiện người (ID 0)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Không thể mở webcam")
    exit()

window_name = 'Canh Bao Xam Nhap (Click chuot trai de ve ROI, click phai de xoa)'
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, handle_mouse)

print("--- HUONG DAN ---")
print("Chuột TRÁI: Thêm điểm vào vùng đa giác")
print("Chuột PHẢI: Xóa vùng đã vẽ")
print("Phím 'q': Thoát chương trình")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Dự đoán
    results = model(frame)
    
    # Lấy thông tin phát hiện
    # result details: xmin, ymin, xmax, ymax, confidence, class, name
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
        
        # Các điểm cần kiểm tra: 4 góc và tâm của khung bao người
        check_points = [
            (x1, y1), (x2, y1), (x1, y2), (x2, y2), # 4 góc
            (int((x1 + x2) / 2), int((y1 + y2) / 2)), # Tâm
            (int((x1 + x2) / 2), y2)                  # Bàn chân (giữa cạnh dưới)
        ]
        
        is_in_this_det = False
        # Kiểm tra nếu bất kỳ điểm nào trong 6 điểm trên nằm trong vùng ROI
        if len(points) > 2:
            for cp in check_points:
                if cv2.pointPolygonTest(np.array(points, np.int32), cp, False) >= 0:
                    is_in_this_det = True
                    break
            
            if is_in_this_det:
                person_in_roi = True
                # Vẽ khung màu đỏ nếu trong vùng
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # Vẽ các điểm kiểm tra để người dùng quan sát
                for cp in check_points:
                    cv2.circle(frame, cp, 3, (0, 0, 255), -1)
            else:
                # Vẽ khung màu xanh nếu ngoài vùng
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        else:
            # Chưa vẽ vùng ROI
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
        # Hiển thị độ tin cậy (Confidence)
        cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if person_in_roi:
        cv2.putText(frame, "CANH BAO: CO NGUOI XAM NHAP!", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        send_telegram_alert("⚠️ Cảnh báo! Phát hiện người đi vào khu vực cấm!", frame)
    else:
        cv2.putText(frame, "Trang thai: Binh thuong", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow(window_name, frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()