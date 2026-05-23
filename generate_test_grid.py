import os
import glob
import random
import cv2
import numpy as np
from ultralytics import YOLO
import shutil

def main():
    val_images_dir = r"d:\CODE\yolo\dataset\val\images"
    val_labels_dir = r"d:\CODE\yolo\dataset\val\labels"
    model_path = r"d:\CODE\yolo\yolov8n_fall_best.pt"
    
    print("==================================================")
    print("STARTING STANDALONE MODEL TEST AND PLOTTING")
    print("==================================================")
    
    # 1. Load trained model
    if not os.path.exists(model_path):
        print(f"[ERROR] Trained model weights not found at: {model_path}")
        return
        
    print(f"[INFO] Loading model: {model_path}...")
    model = YOLO(model_path)
    print("[SUCCESS] Model loaded successfully.")
    
    # 2. Find normal and fall images by reading labels
    label_files = glob.glob(os.path.join(val_labels_dir, "*.txt"))
    normal_img_paths = []
    fall_img_paths = []
    
    print(f"[INFO] Scanning validation label files in: {val_labels_dir}...")
    for lf in label_files:
        basename = os.path.basename(lf)
        img_name = basename.replace(".txt", ".jpg")
        img_path = os.path.join(val_images_dir, img_name)
        
        if not os.path.exists(img_path):
            continue
            
        with open(lf, "r") as f:
            lines = f.readlines()
            
        has_fall = False
        has_normal = False
        for line in lines:
            parts = line.strip().split()
            if len(parts) > 0:
                cls_id = int(parts[0])
                if cls_id == 0: # Class 0 represents Fall
                    has_fall = True
                elif cls_id == 1: # Class 1 represents Normal
                    has_normal = True
                    
        if has_fall:
            fall_img_paths.append(img_path)
        elif has_normal:
            normal_img_paths.append(img_path)
            
    print(f"[INFO] Found {len(normal_img_paths)} normal images and {len(fall_img_paths)} fall images.")
    
    if len(normal_img_paths) < 3 or len(fall_img_paths) < 3:
        print("[ERROR] Not enough validation images for creating test grid (need at least 3 normal and 3 fall).")
        return
        
    # 3. Randomly select 3 of each
    random.seed(42)  # For reproducibility
    selected_normal = random.sample(normal_img_paths, 3)
    selected_fall = random.sample(fall_img_paths, 3)
    
    test_images = selected_normal + selected_fall
    processed_frames = []
    
    # 4. Predict on selected images
    print("\n[INFO] Running inference on 6 selected validation images...")
    for idx, img_path in enumerate(test_images):
        frame = cv2.imread(img_path)
        # Predict
        results = model(frame, verbose=False)
        
        # Draw predictions
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].cpu().item())
                conf = float(box.conf[0].cpu().item())
                x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                
                if cls_id == 0:  # Fall (Class 0 represents fall)
                    color = (0, 0, 255)  # Red
                    label = f"FALL ({conf:.2f})"
                else:  # Normal (Class 1 represents normal)
                    color = (0, 255, 0)  # Green
                    label = f"Normal ({conf:.2f})"
                    
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                # Draw label text background
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(frame, (x1, y1 - th - 4), (x1 + tw, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                            
        # Resize to standard size (320x240) to align in grid
        frame_resized = cv2.resize(frame, (320, 240))
        processed_frames.append(frame_resized)
        print(f"Processed image {idx + 1}/6: {os.path.basename(img_path)}")
        
    # 5. Stitches images into a 2x3 grid
    print("\n[INFO] Creating 2x3 prediction grid...")
    row1 = np.hstack((processed_frames[0], processed_frames[1], processed_frames[2]))
    row2 = np.hstack((processed_frames[3], processed_frames[4], processed_frames[5]))
    grid = np.vstack((row1, row2))
    
    # Add title and labels to the grid
    h, w, _ = grid.shape
    border = np.zeros((60, w, 3), dtype=np.uint8)
    cv2.putText(border, "YOLOv8 CUSTOM MODEL TEST PREDICTIONS", (20, 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(border, "Top Row: Normal Poses  |  Bottom Row: Fall Poses (FALL)", (20, 48), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    final_grid = np.vstack((border, grid))
    
    # 6. Save grid image
    output_path = r"d:\CODE\yolo\test_results_grid.jpg"
    cv2.imwrite(output_path, final_grid)
    print(f"[SUCCESS] Standalone test grid saved at: {output_path}")
    
    # Copy to brain artifact directory
    brain_dir = r"C:\Users\toans\.gemini\antigravity-ide\brain\009e70d0-3bd6-472e-8ba3-7729a781ec2c"
    brain_dest = os.path.join(brain_dir, "test_results_grid.jpg")
    try:
        shutil.copy2(output_path, brain_dest)
        print(f"[INFO] Copied grid image to brain artifact path: {brain_dest}")
    except Exception as e:
        print(f"[WARNING] Could not copy to brain artifact path: {e}")
        
    print("==================================================")

if __name__ == "__main__":
    main()
