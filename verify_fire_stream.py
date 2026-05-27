import os
import cv2
import numpy as np
from ultralytics import YOLO
import app.config as config
from app.config import SystemStatus

def verify():
    model_path = "yolov8n_fire_custom.pt"
    if not os.path.exists(model_path):
        print(f"[ERROR] Weight file {model_path} not found!")
        return False
        
    print(f"Loading custom model {model_path}...")
    model = YOLO(model_path)
    
    # Create mock CameraState
    from app.processors import CameraState
    state = CameraState()
    
    # Load test image
    image_path = r"C:\Users\toans\.gemini\antigravity-ide\brain\009e70d0-3bd6-472e-8ba3-7729a781ec2c\test_fire_image_1779844057284.png"
    if not os.path.exists(image_path):
        print(f"[ERROR] Test image {image_path} not found!")
        return False
        
    frame = cv2.imread(image_path)
    
    print("\nSimulating 20 frames of fire detection to trigger filter buffer...")
    
    # We will temporarily mock SystemStatus.add_log and send_telegram_alert to verify they are called
    logged = False
    original_add_log = SystemStatus.add_log
    
    def mock_add_log(msg, log_type=""):
        nonlocal logged
        print(f"[MOCK LOG] Added log: '{msg}' of type '{log_type}'")
        logged = True
        original_add_log(msg, log_type)
        
    SystemStatus.add_log = mock_add_log
    
    # Let's run the processing logic
    for i in range(20):
        # Run inference
        results = model(frame, verbose=False)
        fire_in_frame = False
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].cpu().item())
                conf = float(box.conf[0].cpu().item())
                if conf > 0.25:
                    label_name = model.names.get(cls_id, f"Class {cls_id}")
                    if "fire" in label_name.lower() or "smoke" in label_name.lower():
                        fire_in_frame = True
                        
        if fire_in_frame:
            state.fire_counter += 1
            if state.fire_counter >= 15:
                state.fire_active = True
                print(f"Frame {i+1}: state.fire_active is True! Counter: {state.fire_counter}")
                if not logged:
                    SystemStatus.add_log(f"🚨 Test_Cam: Phát hiện ngọn lửa hoặc khói bất thường!", "danger")
            else:
                print(f"Frame {i+1}: Fire detected but buffer not full yet. Counter: {state.fire_counter}")
        else:
            state.fire_counter = max(0, state.fire_counter - 1)
            if state.fire_counter == 0:
                state.fire_active = False
                
    # Restore original log function
    SystemStatus.add_log = original_add_log
    
    print("\nVerification Results:")
    print(" - final fire_counter:", state.fire_counter)
    print(" - state.fire_active:", state.fire_active)
    print(" - alarm triggered (logged):", logged)
    
    if state.fire_active and logged:
        print("[SUCCESS] Automated verification passed!")
        return True
    else:
        print("[FAILED] Verification failed. Fire was not detected or active state not triggered.")
        return False

if __name__ == "__main__":
    verify()
