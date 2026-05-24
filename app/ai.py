import os
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from ultralytics import YOLO

# Xác định thiết bị tính toán (GPU CUDA nếu khả dụng, nếu không sử dụng CPU)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"==================================================")
print(f"[AI MODEL] Đang khởi chạy các mô hình trên thiết bị: {device}")
print(f"==================================================")

# 1. FaceNet và MTCNN phục vụ nhận diện khuôn mặt
# mtcnn_single: Dùng cho trang đăng ký khuôn mặt mới (chỉ lấy 1 mặt chính diện)
mtcnn_single = MTCNN(keep_all=False, device=device)
# mtcnn_multi: Dùng cho camera nhận diện thời gian thực (phát hiện nhiều mặt)
mtcnn_multi = MTCNN(keep_all=True, device=device)
# resnet: Trích xuất face embedding vector
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# 2. YOLOv5 cho giám sát xâm nhập vùng cấm (ROI Intrusion)
print("[AI MODEL] Đang nạp YOLOv5...")
yolov5_model = torch.hub.load("ultralytics/yolov5", "yolov5s").to(device)
yolov5_model.classes = [0]  # Chỉ nhận diện lớp Người (Person)
yolov5_model.conf = 0.4     # Ngưỡng tin cậy mặc định cho ROI

# 3. YOLOv8 cho bộ đếm người qua vạch kép (Counter)
print("[AI MODEL] Đang nạp YOLOv8 (yolov8s.pt)...")
yolov8_model = YOLO("yolov8s.pt")
yolov8_model.to(device)

# 4. YOLOv8-pose cho phát hiện ngã (Ước lượng tư thế xương)
print("[AI MODEL] Đang nạp YOLOv8-pose...")
yolov8_pose_model = YOLO("yolov8n-pose.pt")
yolov8_pose_model.to(device)

# 4b. YOLOv8-fall tự huấn luyện dành riêng cho phát hiện người ngã
yolov8_fall_model_path = "yolov8n_fall_best.pt"
yolov8_fall_model = None
if os.path.exists(yolov8_fall_model_path):
    print(f"[AI MODEL] Phát hiện mô hình ngã tự train: {yolov8_fall_model_path}. Đang nạp...")
    try:
        yolov8_fall_model = YOLO(yolov8_fall_model_path)
        yolov8_fall_model.to(device)
        print("[AI MODEL] Đã nạp thành công mô hình ngã tự train!")
    except Exception as e:
        print(f"[AI MODEL] [ERROR] Lỗi nạp mô hình ngã tự train: {e}")
else:
    print("[AI MODEL] Không tìm thấy mô hình ngã tự train. Sử dụng pose estimation làm dự phòng.")
