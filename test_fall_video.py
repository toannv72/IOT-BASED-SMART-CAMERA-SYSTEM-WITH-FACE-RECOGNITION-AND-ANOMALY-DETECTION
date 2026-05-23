import os
import sys
import argparse
import cv2
import numpy as np
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Fall Detection - Video Tester")
    parser.add_argument("video", nargs="?", default="videotest/1.mp4", help="Path to video file")
    parser.add_argument("--mode", "-m", choices=["custom", "pose"], default="custom", 
                        help="Detection mode: 'custom' (YOLOv8-fall custom model) or 'pose' (YOLOv8-pose keypoint heuristic)")
    args = parser.parse_args()
    
    video_path = args.video
    mode = args.mode
    
    print("==================================================")
    print("YOLOv8 FALL DETECTION - VIDEO TESTER")
    print("==================================================")
    print(f"Video Source: {video_path}")
    print(f"Mode: {mode.upper()}")
    
    # 2. Check source video file
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found at: {video_path}")
        print("Please provide a valid video file path.")
        return

    # 3. Load model
    device = "cuda" if cv2.ocl.haveOpenCL() else "cpu"  # Let YOLO choose device or force it
    
    if mode == "custom":
        model_path = "yolov8n_fall_best.pt"
        if not os.path.exists(model_path):
            print(f"[ERROR] Trained weights file not found at: {model_path}")
            return
        print("[INFO] Loading custom YOLOv8-fall model...")
        model = YOLO(model_path)
    else:
        model_path = "yolov8n-pose.pt"
        print("[INFO] Loading YOLOv8-pose model...")
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
    
    window_name = f"Fall Detection Test ({mode.upper()}) - {os.path.basename(video_path)}"
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
        fall_in_frame = False
        
        # Inference
        results = model(frame, verbose=False)
        
        if mode == "custom":
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].cpu().item())
                    conf = float(box.conf[0].cpu().item())
                    
                    if conf > 0.4:
                        x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                        
                        if cls_id == 0:  # Fall
                            color = (0, 0, 255)  # Red
                            label = f"FALL ({conf:.2f})"
                            fall_in_frame = True
                        else:  # Normal
                            color = (0, 255, 0)  # Green
                            label = f"Normal ({conf:.2f})"
                            
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
                        cv2.putText(frame, label, (x1, y1 - 4), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        else: # pose mode
            if len(results) > 0 and results[0].keypoints is not None:
                keypoints_data = results[0].keypoints.data.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                
                for i, kpts in enumerate(keypoints_data):
                    if i >= len(boxes):
                        break
                    box = boxes[i]
                    x1, y1, x2, y2 = [int(b) for b in box[:4]]
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    
                    l_sho = kpts[5]
                    r_sho = kpts[6]
                    l_hip = kpts[11]
                    r_hip = kpts[12]
                    l_ank = kpts[15]
                    r_ank = kpts[16]
                    
                    has_conf = kpts.shape[1] == 3
                    
                    sho_x = (l_sho[0] + r_sho[0]) / 2
                    sho_y = (l_sho[1] + r_sho[1]) / 2
                    hip_x = (l_hip[0] + r_hip[0]) / 2
                    hip_y = (l_hip[1] + r_hip[1]) / 2
                    ank_x = (l_ank[0] + r_ank[0]) / 2
                    ank_y = (l_ank[1] + r_ank[1]) / 2
                    
                    is_horizontal = False
                    
                    sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                    hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0
                    ank_conf = min(l_ank[2], r_ank[2]) if has_conf else 1.0
                    
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        dy = sho_y - hip_y
                        dx = sho_x - hip_x
                        angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                        if angle_body < 40 or angle_body > 140:
                            is_horizontal = True
                            
                    if not is_horizontal and sho_conf > 0.3 and ank_conf > 0.3:
                        dy_full = ank_y - sho_y
                        dx_full = ank_x - sho_x
                        angle_full = abs(np.arctan2(dy_full, dx_full) * 180 / np.pi)
                        if angle_full < 40 or angle_full > 140:
                            is_horizontal = True
                            
                    if not is_horizontal and aspect_ratio > 1.3:
                        is_horizontal = True
                        
                    color = (0, 255, 0)
                    label = "Normal"
                    if is_horizontal:
                        color = (0, 0, 255)
                        label = "FALL (Pose)"
                        fall_in_frame = True
                        
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
                    cv2.putText(frame, label, (x1, y1 - 4), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                                
                    # Optional: draw keypoint lines
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        cv2.line(frame, (int(sho_x), int(sho_y)), (int(hip_x), int(hip_y)), (255, 255, 0), 2)
                    if hip_conf > 0.3 and ank_conf > 0.3:
                        cv2.line(frame, (int(hip_x), int(hip_y)), (int(ank_x), int(ank_y)), (255, 0, 255), 2)

        # Threat assessment / Alert state
        if fall_in_frame:
            fall_counter += 1
            if fall_counter >= 12:  # consecutive frames
                cv2.putText(frame, "ALERT: FALL DETECTED!", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            fall_counter = max(0, fall_counter - 1)
            
        # Draw status overlay
        status_text = f"Frames: {frame_count} | Mode: {mode.upper()}"
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
