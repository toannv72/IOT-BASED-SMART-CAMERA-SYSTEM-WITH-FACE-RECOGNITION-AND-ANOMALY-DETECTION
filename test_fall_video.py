import os
import sys
import cv2
from ultralytics import YOLO

def main():
    # 1. Configuration
    model_path = "yolov8n_fall_best.pt"
    
    # Default video path or take from argument
    video_path = "kaggle_cache/datasets/tuyenldvn/falldataset-imvia/versions/2/Home_02/Home_02/Videos/video (31).avi"
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
    print("==================================================")
    print("YOLOv8 CUSTOM FALL DETECTION - VIDEO TESTER")
    print("==================================================")
    print(f"Model: {model_path}")
    print(f"Video Source: {video_path}")
    
    # 2. Check model existence
    if not os.path.exists(model_path):
        print(f"[ERROR] Trained weights file not found at: {model_path}")
        print("Please train the model first or make sure it is in the root directory.")
        return
        
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found at: {video_path}")
        print("Please provide a valid video file path.")
        return

    # 3. Load model
    print("[INFO] Loading custom YOLOv8 model...")
    model = YOLO(model_path)
    print("[SUCCESS] Model loaded successfully.")
    
    # 4. Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] Video resolution: {width}x{height} | FPS: {fps:.2f}")
    print("[INFO] Starting playback. Press 'q' key to quit.")
    
    window_name = f"Fall Detection Test - {os.path.basename(video_path)}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 600)
    
    frame_count = 0
    fall_counter = 0
    
    # 5. Process loop
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] End of video or cannot read frame.")
            break
            
        frame_count += 1
        
        # Inference
        results = model(frame, verbose=False)
        fall_in_frame = False
        
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].cpu().item())
                conf = float(box.conf[0].cpu().item())
                
                # Check confidence threshold (0.4 is optimal)
                if conf > 0.4:
                    x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                    
                    if cls_id == 0:  # Fall (Class 0 mapped to fall)
                        color = (0, 0, 255)  # Red
                        label = f"FALL ({conf:.2f})"
                        fall_in_frame = True
                    else:  # Normal (Class 1 mapped to normal)
                        color = (0, 255, 0)  # Green
                        label = f"Normal ({conf:.2f})"
                        
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    # Text background
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
                    cv2.putText(frame, label, (x1, y1 - 4), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Threat assessment / Alert state
        if fall_in_frame:
            fall_counter += 1
            if fall_counter >= 12:  # consecutive frames
                cv2.putText(frame, "ALERT: FALL DETECTED!", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            fall_counter = max(0, fall_counter - 1)
            
        # Draw status overlay
        status_text = f"Frames: {frame_count} | Mode: Custom Model"
        cv2.putText(frame, status_text, (20, height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    
        # Show frame
        cv2.imshow(window_name, frame)
        
        # Adjust playback speed (waitKey match video fps)
        delay = int(1000 / fps) if fps > 0 else 30
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            print("[INFO] Quitting test script...")
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("==================================================")
    print("TEST COMPLETED")
    print("==================================================")

if __name__ == "__main__":
    main()
