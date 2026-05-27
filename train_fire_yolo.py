import os
import shutil
from ultralytics import YOLO

def train():
    data_yaml_path = r"d:\CODE\yolo\dataset_fire\data.yaml"
    if not os.path.exists(data_yaml_path):
        print(f"[ERROR] Configuration file not found: {data_yaml_path}. Run copy_and_prepare_dataset.py first!")
        return
        
    print("==================================================")
    print("[SYSTEM] Starting YOLOv8 Fire Detection Model Training")
    print("==================================================")
    
    # Khởi tạo mô hình YOLOv8n (nano) phát hiện đối tượng
    model = YOLO("yolov8n.pt")
    
    # Tiến hành training
    # Sử dụng imgsz=640 để có chất lượng nhận diện tốt nhất, hoặc imgsz=320 để train cực nhanh
    # epochs=15 là hợp lý để mô hình hội tụ nhanh chóng trên tập dữ liệu nhỏ
    results = model.train(
        data=data_yaml_path,
        epochs=15,
        imgsz=640,
        batch=16,
        device=0,         # Sử dụng GPU CUDA thứ nhất
        workers=2,        # Số luồng tải dữ liệu
        project="runs/train_fire",
        name="yolov8n_fire"
    )
    
    print("\n==================================================")
    print("[SYSTEM] Training completed successfully!")
    
    # Tìm kiếm file weight tốt nhất
    best_weight_options = [
        os.path.join("runs", "detect", "runs", "train_fire", "yolov8n_fire", "weights", "best.pt"),
        os.path.join("runs", "train_fire", "yolov8n_fire", "weights", "best.pt")
    ]
    best_weight = None
    for opt in best_weight_options:
        if os.path.exists(opt):
            best_weight = opt
            break
            
    if best_weight is not None:
        print(f"[SYSTEM] Best model weights saved at: {best_weight}")
        # Sao chép file weight tốt nhất ra thư mục gốc
        shutil_dest = os.path.join("d:\\CODE\\yolo", "yolov8n_fire_custom.pt")
        shutil.copy2(best_weight, shutil_dest)
        print(f"[SYSTEM] Copied model to workspace root: {shutil_dest}")
    else:
        print("[ERROR] Best model weights file not found in any expected location!")
    print("==================================================")

if __name__ == "__main__":
    train()
