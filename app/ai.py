import os
import torch
import numpy as np

# Xác định thiết bị tính toán (GPU CUDA nếu khả dụng, nếu không sử dụng CPU)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"==================================================")
print(f"[AI MODEL] Compute device configured: {device}")
print(f"==================================================")

# Biến private lưu trữ các thực thể singleton của mô hình
_mtcnn_single = None
_mtcnn_multi = None
_resnet = None
_yolov5_model = None
_yolov8_model = None
_yolov8_pose_model = None
_yolov8_fall_model = None
_yolov8_fire_model = None

# Hàm hâm nóng (warmup) mô hình để tránh race condition trong các luồng chạy nền
def _warmup_yolo_model(model):
    try:
        dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
        model(dummy_frame, verbose=False)
    except Exception as e:
        print(f"[AI MODEL] [WARNING] Model warmup failed (non-critical): {e}")

def __getattr__(name):
    global _mtcnn_single, _mtcnn_multi, _resnet, _yolov5_model, _yolov8_model, _yolov8_pose_model, _yolov8_fall_model, _yolov8_fire_model
    
    if name == 'mtcnn_single':
        if _mtcnn_single is None:
            from facenet_pytorch import MTCNN
            print("[AI MODEL] [LAZY] Loading MTCNN (single)...")
            _mtcnn_single = MTCNN(keep_all=False, thresholds=[0.5, 0.6, 0.6], device=device)
        return _mtcnn_single
        
    elif name == 'mtcnn_multi':
        if _mtcnn_multi is None:
            from facenet_pytorch import MTCNN
            print("[AI MODEL] [LAZY] Loading MTCNN (multi)...")
            _mtcnn_multi = MTCNN(keep_all=True, thresholds=[0.5, 0.6, 0.6], device=device)
        return _mtcnn_multi
        
    elif name == 'resnet':
        if _resnet is None:
            from facenet_pytorch import InceptionResnetV1
            print("[AI MODEL] [LAZY] Loading FaceNet (InceptionResnetV1)...")
            _resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
        return _resnet
        
    elif name == 'yolov5_model':
        if _yolov5_model is None:
            print("[AI MODEL] [LAZY] Loading YOLOv5 (yolov5n)...")
            # Đổi sang yolov5n (Nano) để siêu nhẹ và chạy cực nhanh trên CPU Pi
            _yolov5_model = torch.hub.load("ultralytics/yolov5", "yolov5n").to(device)
            _yolov5_model.classes = [0]  # Chỉ nhận diện lớp Người (Person)
            _yolov5_model.conf = 0.4     # Ngưỡng tin cậy mặc định cho ROI
            # Hâm nóng yolov5
            try:
                dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
                _yolov5_model(dummy_frame)
            except Exception:
                pass
        return _yolov5_model
        
    elif name == 'yolov8_model':
        if _yolov8_model is None:
            from ultralytics import YOLO
            # Đổi sang yolov8n.pt (Nano) để chạy cực nhanh trên CPU Pi thay vì yolov8s.pt nặng nề
            print("[AI MODEL] [LAZY] Loading YOLOv8 (yolov8n.pt)...")
            _yolov8_model = YOLO("yolov8n.pt")
            _yolov8_model.to(device)
            _warmup_yolo_model(_yolov8_model)
        return _yolov8_model
        
    elif name == 'yolov8_pose_model':
        if _yolov8_pose_model is None:
            from ultralytics import YOLO
            print("[AI MODEL] [LAZY] Loading YOLOv8-pose...")
            _yolov8_pose_model = YOLO("yolov8n-pose.pt")
            _yolov8_pose_model.to(device)
            _warmup_yolo_model(_yolov8_pose_model)
        return _yolov8_pose_model
        
    elif name == 'yolov8_fall_model':
        if _yolov8_fall_model is None:
            yolov8_fall_model_path = "yolov8n_fall_best.pt"
            if os.path.exists(yolov8_fall_model_path):
                from ultralytics import YOLO
                print(f"[AI MODEL] [LAZY] Custom fall model found: {yolov8_fall_model_path}. Loading...")
                try:
                    _yolov8_fall_model = YOLO(yolov8_fall_model_path)
                    _yolov8_fall_model.to(device)
                    _warmup_yolo_model(_yolov8_fall_model)
                except Exception as e:
                    print(f"[AI MODEL] [ERROR] Loading custom fall model failed: {e}")
            else:
                print("[AI MODEL] [WARNING] Custom fall model not found.")
        return _yolov8_fall_model
        
    elif name == 'yolov8_fire_model':
        if _yolov8_fire_model is None:
            from ultralytics import YOLO
            yolov8_fire_custom_path = "yolov8n_fire_custom.pt"
            yolov8_fire_fallback_path = "yolov8n_fire.pt"
            if os.path.exists(yolov8_fire_custom_path):
                print(f"[AI MODEL] [LAZY] Custom fire model found: {yolov8_fire_custom_path}. Loading...")
                try:
                    _yolov8_fire_model = YOLO(yolov8_fire_custom_path)
                    _yolov8_fire_model.to(device)
                    _warmup_yolo_model(_yolov8_fire_model)
                except Exception as e:
                    print(f"[AI MODEL] [ERROR] Loading custom fire model failed: {e}")
            elif os.path.exists(yolov8_fire_fallback_path):
                print(f"[AI MODEL] [LAZY] Using fallback fire model: {yolov8_fire_fallback_path}. Loading...")
                try:
                    _yolov8_fire_model = YOLO(yolov8_fire_fallback_path)
                    _yolov8_fire_model.to(device)
                    _warmup_yolo_model(_yolov8_fire_model)
                except Exception as e:
                    print(f"[AI MODEL] [ERROR] Loading fallback fire model failed: {e}")
        return _yolov8_fire_model
        
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
