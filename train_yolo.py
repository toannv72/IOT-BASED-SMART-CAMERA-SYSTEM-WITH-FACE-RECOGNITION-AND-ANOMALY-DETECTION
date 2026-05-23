import os
from ultralytics import YOLO

def train():
    data_yaml_path = r"d:\CODE\yolo\dataset\data.yaml"
    if not os.path.exists(data_yaml_path):
        print(f"[ERROR] Configuration file not found: {data_yaml_path}. Run preprocess_dataset.py first!")
        return
        
    print("==================================================")
    print("[SYSTEM] Starting YOLOv8 Fall Detection Model Training")
    print("==================================================")
    
    # Khởi tạo mô hình YOLOv8n (nano) phát hiện đối tượng
    model = YOLO("yolov8n.pt")
    
    # Tiến hành training
    # imgsz=320 phù hợp với độ phân giải video gốc (320x240) và giúp huấn luyện cực nhanh.
    # batch=32 phù hợp với VRAM 4GB của card đồ họa RTX 3050 Laptop.
    results = model.train(
        data=data_yaml_path,
        epochs=30,
        imgsz=320,
        batch=32,
        device=0,         # Sử dụng GPU CUDA thứ nhất
        workers=2,        # Số luồng tải dữ liệu (tránh nghẽn CPU)
        project="runs/train_fall",
        name="yolov8n_fall"
    )
    
    print("\n==================================================")
    print("[SYSTEM] Training completed successfully!")
    # Đường dẫn file weight tốt nhất (YOLOv8 mặc định lưu dưới runs/detect)
    best_weight_options = [
        os.path.join("runs", "detect", "runs", "train_fall", "yolov8n_fall", "weights", "best.pt"),
        os.path.join("runs", "train_fall", "yolov8n_fall", "weights", "best.pt")
    ]
    best_weight = None
    for opt in best_weight_options:
        if os.path.exists(opt):
            best_weight = opt
            break
            
    if best_weight is not None:
        print(f"[SYSTEM] Best model weights saved at: {best_weight}")
        # Sao chép file weight tốt nhất ra thư mục gốc
        shutil_dest = os.path.join("d:\\CODE\\yolo", "yolov8n_fall_best.pt")
        import shutil
        shutil.copy2(best_weight, shutil_dest)
        print(f"[SYSTEM] Copied model to workspace root: {shutil_dest}")
    else:
        print("[ERROR] Best model weights file not found in any expected location!")
    print("==================================================")

if __name__ == "__main__":
    train()
