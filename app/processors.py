import os
import cv2
import time
import math
import numpy as np
import json
import collections
from PIL import Image
import torch
import supervision as sv

# Import các biến cấu hình và mô hình AI từ các package
import app.config as config
from app.config import SystemStatus
from app.ai import device, mtcnn_multi, resnet, yolov5_model, yolov8_model, yolov8_pose_model, yolov8_fall_model
from app.alerts import send_telegram_alert
from app.database import SessionLocal, FaceRecord

# Biến lưu trữ FPS đo được thời gian thực cho từng luồng camera
camera_fps = {
    "face": 0.0,
    "roi": 0.0,
    "counter": 0.0,
    "fall": 0.0
}

# =========================================================================
# LUỒNG 1: LUỒNG NHẬN DIỆN KHUÔN MẶT (FACE RECOGNITION)
# =========================================================================
def gen_face_stream():
    # 1. Nạp trước các vector nhúng (embeddings) và tên từ database SQLite
    db = SessionLocal()
    records = db.query(FaceRecord).all()
    db.close()
    
    names = [r.name for r in records]
    db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])
    
    # 2. Mở Camera chính diện (Webcam 0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[PROCESSORS] [ERROR] Không thể mở webcam cho luồng khuôn mặt!")
        return

    THRESHOLD = 0.8  # Ngưỡng cosine distance để nhận diện người quen
    frame_cnt = 0
    print("[PROCESSORS] Khởi tạo thành công luồng nhận diện khuôn mặt.")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            break
            
        # Tự động nạp lại embeddings sau mỗi 60 frames để cập nhật đăng ký mới mà không cần khởi động lại
        frame_cnt += 1
        if frame_cnt % 60 == 0:
            db = SessionLocal()
            records = db.query(FaceRecord).all()
            db.close()
            names = [r.name for r in records]
            db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])

        # 3. Phát hiện khuôn mặt bằng MTCNN
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        boxes, _ = mtcnn_multi.detect(img_pil)
        
        if boxes is not None:
            faces = mtcnn_multi(img_pil)
            if faces is not None:
                # Trích xuất đặc trưng embedding
                embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                
                for box, emb in zip(boxes, embeddings):
                    x1, y1, x2, y2 = [int(b) for b in box]
                    best_match_name = "Unknown"
                    best_distance = float("inf")
                    
                    # 4. So khớp khoảng cách Euclid/Cosine với CSDL
                    if len(db_embeddings) > 0:
                        distances = np.linalg.norm(db_embeddings - emb, axis=1)
                        min_idx = np.argmin(distances)
                        min_dist = distances[min_idx]
                        
                        if min_dist < THRESHOLD:
                            best_match_name = names[min_idx]
                            best_distance = min_dist
                            
                    # 5. Vẽ box và nhãn tên lên khung hình
                    color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    # 6. Kích hoạt cảnh báo Telegram bất đồng bộ nếu phát hiện người lạ
                    if best_match_name == "Unknown":
                        SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người lạ (Unknown) trước cửa!", "danger")
                        send_telegram_alert(
                            message="⚠️ [CẢNH BÁO FACE] Phát hiện người lạ (Unknown) xuất hiện tại Camera Nhận Diện Khuôn Mặt!",
                            frame=frame,
                            alert_type="face",
                            camera_id="Cam_Khuon_Mat"
                        )
        
        # 7. Nén thành file ảnh JPEG trả về cho trình duyệt
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: 
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        # Đo lường tốc độ khung hình
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["face"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 2: LUỒNG GIÁM SÁT XÂM NHẬP VÙNG CẤM (ROI INTRUSION)
# =========================================================================
def gen_roi_stream():
    video_path = "video1.mp4"
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[PROCESSORS] [ERROR] Không thể mở video ROI: {video_path}")
        return

    # Tải vùng đa giác ROI cấu hình từ file
    ROI_FILE = "roi_video.json"
    points = []
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                points = json.load(f)
        except Exception:
            pass
            
    if len(points) < 3:
        points = [[150, 150], [550, 150], [580, 450], [120, 450]]

    print("[PROCESSORS] Khởi tạo thành công luồng cảnh báo xâm nhập ROI.")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        # 1. Phát hiện người bằng YOLOv5s
        results = yolov5_model(frame)
        detections = results.xyxy[0].cpu().numpy()
        
        person_in_roi = False
        
        # Vẽ đa giác ROI màu vàng lên hình
        pts = np.array(points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
        
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Chỉ lấy các hộp có độ tự tin cao hơn cấu hình động
            if conf < config.settings.get("conf_threshold", 0.25):
                continue
                
            # Điểm chân và điểm tâm người dùng để so khớp trong ROI
            check_points = [
                (int((x1 + x2) / 2), y2),
                (int((x1 + x2) / 2), int((y1 + y2) / 2))
            ]
            
            is_in_this_det = False
            for cp in check_points:
                if cv2.pointPolygonTest(np.array(points, np.int32), cp, False) >= 0:
                    is_in_this_det = True
                    break
                    
            if is_in_this_det:
                person_in_roi = True
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Đỏ khi xâm nhập
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Xanh khi ngoài ROI
                
            cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 2. Xử lý trạng thái cảnh báo xâm nhập
        if person_in_roi:
            SystemStatus.intrusion_active = True
            cv2.putText(frame, "CANH BAO: XAM NHAP ROI!", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người xâm nhập vùng cấm!", "danger")
            
            # Gửi cảnh báo Telegram bất đồng bộ (Thread) không treo luồng
            send_telegram_alert(
                message="⚠️ [CẢNH BÁO ROI] Phát hiện người xâm nhập trái phép vùng cấm bảo mật!",
                frame=frame,
                alert_type="intrusion",
                camera_id="Cam_Cua_Chinh_ROI"
            )
        else:
            SystemStatus.intrusion_active = False
            cv2.putText(frame, "Trang thai: Binh thuong", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: 
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["roi"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 3: LUỒNG ĐẾM NGƯỜI VẠCH ĐÔI SONG SONG (DOUBLE-LINE COUNTER)
# =========================================================================
def gen_counter_stream():
    cameras = config.get_cameras_config()
    cam1_cfg = next((c for c in cameras if c["camera_id"] == "Cam_Cua_Chinh"), cameras[0])
    cam2_cfg = next((c for c in cameras if c["camera_id"] == "Cam_Cua_Sau"), cameras[1])
    
    cap1 = cv2.VideoCapture(cam1_cfg["source"])
    cap2 = cv2.VideoCapture(cam2_cfg["source"])
    
    def get_cam_double_lines(cfg):
        x1, y1 = cfg["line"][0]
        x2, y2 = cfg["line"][1]
        
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: length = 1.0
        
        nx = -dy / length
        ny = dx / length
        d = 30.0
        
        in_dir = cfg.get("in_direction", "down")
        if in_dir == "down":
            dot = ny
        elif in_dir == "up":
            dot = -ny
        elif in_dir == "right":
            dot = nx
        elif in_dir == "left":
            dot = -nx
        else:
            dot = 1.0
            
        if dot >= 0:
            outside_reg = 1
            inside_reg = 3
            line_outer_A = (int(x1 - d * nx), int(y1 - d * ny))
            line_outer_B = (int(x2 - d * nx), int(y2 - d * ny))
            line_inner_A = (int(x1 + d * nx), int(y1 + d * ny))
            line_inner_B = (int(x2 + d * nx), int(y2 + d * ny))
        else:
            outside_reg = 3
            inside_reg = 1
            line_outer_A = (int(x1 + d * nx), int(y1 + d * ny))
            line_outer_B = (int(x2 + d * nx), int(y2 + d * ny))
            line_inner_A = (int(x1 - d * nx), int(y1 - d * ny))
            line_inner_B = (int(x2 - d * nx), int(y2 - d * ny))
            
        return nx, ny, outside_reg, inside_reg, line_outer_A, line_outer_B, line_inner_A, line_inner_B

    # Tạo vạch đôi song song cho 2 camera
    nx_1, ny_1, outside_reg_1, inside_reg_1, l_out_A_1, l_out_B_1, l_in_A_1, l_in_B_1 = get_cam_double_lines(cam1_cfg)
    nx_2, ny_2, outside_reg_2, inside_reg_2, l_out_A_2, l_out_B_2, l_in_A_2, l_in_B_2 = get_cam_double_lines(cam2_cfg)
    
    count_in_1, count_out_1 = 0, 0
    count_in_2, count_out_2 = 0, 0
    
    track_states1, lost_tracks1, active_tracks1, frame_index1 = {}, {}, {}, 0
    track_states2, lost_tracks2, active_tracks2, frame_index2 = {}, {}, {}, 0
    
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    
    print("[PROCESSORS] Khởi tạo thành công luồng đếm người qua vạch kép đa kênh.")
    
    while True:
        t_start = time.time()
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not ret1 or not ret2:
            # Tự động đồng bộ vạch đếm nếu người dùng vẽ vạch mới trên giao diện OpenCV
            try:
                new_cams = config.get_cameras_config()
                cam1_cfg = next((c for c in new_cams if c["camera_id"] == "Cam_Cua_Chinh"), cam1_cfg)
                cam2_cfg = next((c for c in new_cams if c["camera_id"] == "Cam_Cua_Sau"), cam2_cfg)
            except Exception:
                pass
                
            if not ret1:
                cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
                nx_1, ny_1, outside_reg_1, inside_reg_1, l_out_A_1, l_out_B_1, l_in_A_1, l_in_B_1 = get_cam_double_lines(cam1_cfg)
                track_states1.clear()
                lost_tracks1.clear()
                active_tracks1.clear()
                frame_index1 = 0
            if not ret2:
                cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
                nx_2, ny_2, outside_reg_2, inside_reg_2, l_out_A_2, l_out_B_2, l_in_A_2, l_in_B_2 = get_cam_double_lines(cam2_cfg)
                track_states2.clear()
                lost_tracks2.clear()
                active_tracks2.clear()
                frame_index2 = 0
            continue

        # --- XỬ LÝ CAMERA 1 ---
        frame_index1 += 1
        # Sử dụng ngưỡng tin cậy cấu hình động
        conf_thr = config.settings.get("conf_threshold", 0.25)
        cooldown_thr = config.settings.get("counter_cooldown", 45)
        
        results1 = yolov8_model.track(frame1, persist=True, tracker="custom_bytetrack.yaml", conf=conf_thr, classes=[0], verbose=False, device=device)
        detections1 = sv.Detections.from_ultralytics(results1[0])
        detections1 = detections1[detections1.class_id == 0]
        
        diff_in_1 = 0
        diff_out_1 = 0
        x1_1, y1_1 = cam1_cfg["line"][0]
        d = 30.0
        current_active_tids1 = set()
        
        if detections1.tracker_id is not None and len(detections1.tracker_id) == len(detections1):
            for i, tid in enumerate(detections1.tracker_id):
                current_active_tids1.add(tid)
                bbox = detections1.xyxy[i]
                curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                
                # Bám vết kế thừa
                if tid not in track_states1:
                    best_match_tid = None
                    best_match_dist = float('inf')
                    bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                    for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(lost_tracks1.items()):
                        if lost_tid != tid and frame_index1 - lost_frame < cooldown_thr:
                            dist = math.dist(curr_bc, lost_pos)
                            max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (frame_index1 - lost_frame))
                            if dist < max_dist and dist < best_match_dist:
                                best_match_tid = lost_tid
                                best_match_dist = dist
                    if best_match_tid is not None:
                        lost_state_tuple, _, _ = lost_tracks1[best_match_tid]
                        if lost_state_tuple is not None:
                            track_states1[tid] = lost_state_tuple
                            print(f"[PROCESSORS] [CAM 1] [INHERIT] ID #{tid} kế thừa từ ID #{best_match_tid} (d: {best_match_dist:.1f}px)")
                        if best_match_tid in lost_tracks1: del lost_tracks1[best_match_tid]
                        if best_match_tid in track_states1: del track_states1[best_match_tid]
                        
                active_tracks1[tid] = curr_bc
                if tid in lost_tracks1: del lost_tracks1[tid]
                
                # Chiếu tọa độ lên pháp tuyến vạch kẻ
                x, y = curr_bc
                v = (x - x1_1) * nx_1 + (y - y1_1) * ny_1
                region = 1 if v < -d else (3 if v > d else 2)
                
                # Máy trạng thái với Cooldown khử rung
                state_tuple = track_states1.get(tid)
                state, last_cross = state_tuple if state_tuple is not None else (None, 0)
                
                if region == outside_reg_1:
                    if state == 'from_inside':
                        if frame_index1 - last_cross > cooldown_thr:
                            diff_out_1 += 1
                            track_states1[tid] = ('from_outside', frame_index1)
                            print(f"[PROCESSORS] [CAM 1] ID #{tid} hoàn thành Vượt vạch OUT.")
                    else:
                        track_states1[tid] = ('from_outside', last_cross)
                elif region == inside_reg_1:
                    if state == 'from_outside':
                        if frame_index1 - last_cross > cooldown_thr:
                            diff_in_1 += 1
                            track_states1[tid] = ('from_inside', frame_index1)
                            print(f"[PROCESSORS] [CAM 1] ID #{tid} hoàn thành Vượt vạch IN.")
                    else:
                        track_states1[tid] = ('from_inside', last_cross)
                    
        # Dọn dẹp và cập nhật trạng thái mất dấu
        for tid in list(active_tracks1.keys()):
            if tid not in current_active_tids1:
                last_pos = active_tracks1[tid]
                state_tuple = track_states1.get(tid)
                if state_tuple is not None:
                    lost_tracks1[tid] = (state_tuple, last_pos, frame_index1)
                del active_tracks1[tid]
                    
        for tid in list(track_states1.keys()):
            if tid not in current_active_tids1:
                if tid in lost_tracks1:
                    _, _, lost_frame = lost_tracks1[tid]
                    if frame_index1 - lost_frame > 150:
                        del track_states1[tid]
                        del lost_tracks1[tid]
                else:
                    del track_states1[tid]
                
        if diff_in_1 > 0 or diff_out_1 > 0:
            count_in_1 += diff_in_1
            count_out_1 += diff_out_1
            # Ghi nhận log sự kiện và gửi Telegram
            if diff_in_1 > 0:
                SystemStatus.add_log(f"📥 CAM 1: Có {diff_in_1} người đi VÀO", "success")
                send_telegram_alert(f"📥 [CAM 1] Có {diff_in_1} người vừa đi vào cửa chính.", frame1, "counter", "Cam_Cua_Chinh")
            if diff_out_1 > 0:
                SystemStatus.add_log(f"📤 CAM 1: Có {diff_out_1} người đi RA", "info")
                send_telegram_alert(f"📤 [CAM 1] Có {diff_out_1} người vừa đi ra cửa chính.", frame1, "counter", "Cam_Cua_Chinh")
        
        # --- XỬ LÝ CAMERA 2 ---
        frame_index2 += 1
        results2 = yolov8_model.track(frame2, persist=True, tracker="custom_bytetrack.yaml", conf=conf_thr, classes=[0], verbose=False, device=device)
        detections2 = sv.Detections.from_ultralytics(results2[0])
        detections2 = detections2[detections2.class_id == 0]
        
        diff_in_2 = 0
        diff_out_2 = 0
        x1_2, y1_2 = cam2_cfg["line"][0]
        current_active_tids2 = set()
        
        if detections2.tracker_id is not None and len(detections2.tracker_id) == len(detections2):
            for i, tid in enumerate(detections2.tracker_id):
                current_active_tids2.add(tid)
                bbox = detections2.xyxy[i]
                curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                
                if tid not in track_states2:
                    best_match_tid = None
                    best_match_dist = float('inf')
                    bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                    for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(lost_tracks2.items()):
                        if lost_tid != tid and frame_index2 - lost_frame < cooldown_thr:
                            dist = math.dist(curr_bc, lost_pos)
                            max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (frame_index2 - lost_frame))
                            if dist < max_dist and dist < best_match_dist:
                                best_match_tid = lost_tid
                                best_match_dist = dist
                    if best_match_tid is not None:
                        lost_state_tuple, _, _ = lost_tracks2[best_match_tid]
                        if lost_state_tuple is not None:
                            track_states2[tid] = lost_state_tuple
                            print(f"[PROCESSORS] [CAM 2] [INHERIT] ID #{tid} kế thừa từ ID #{best_match_tid} (d: {best_match_dist:.1f}px)")
                        if best_match_tid in lost_tracks2: del lost_tracks2[best_match_tid]
                        if best_match_tid in track_states2: del track_states2[best_match_tid]
                        
                active_tracks2[tid] = curr_bc
                if tid in lost_tracks2: del lost_tracks2[tid]
                
                x, y = curr_bc
                v = (x - x1_2) * nx_2 + (y - y1_2) * ny_2
                region = 1 if v < -d else (3 if v > d else 2)
                
                state_tuple = track_states2.get(tid)
                state, last_cross = state_tuple if state_tuple is not None else (None, 0)
                
                if region == outside_reg_2:
                    if state == 'from_inside':
                        if frame_index2 - last_cross > cooldown_thr:
                            diff_out_2 += 1
                            track_states2[tid] = ('from_outside', frame_index2)
                            print(f"[PROCESSORS] [CAM 2] ID #{tid} hoàn thành Vượt vạch OUT.")
                    else:
                        track_states2[tid] = ('from_outside', last_cross)
                elif region == inside_reg_2:
                    if state == 'from_outside':
                        if frame_index2 - last_cross > cooldown_thr:
                            diff_in_2 += 1
                            track_states2[tid] = ('from_inside', frame_index2)
                            print(f"[PROCESSORS] [CAM 2] ID #{tid} hoàn thành Vượt vạch IN.")
                    else:
                        track_states2[tid] = ('from_inside', last_cross)
                    
        for tid in list(active_tracks2.keys()):
            if tid not in current_active_tids2:
                last_pos = active_tracks2[tid]
                state_tuple = track_states2.get(tid)
                if state_tuple is not None:
                    lost_tracks2[tid] = (state_tuple, last_pos, frame_index2)
                del active_tracks2[tid]
                    
        for tid in list(track_states2.keys()):
            if tid not in current_active_tids2:
                if tid in lost_tracks2:
                    _, _, lost_frame = lost_tracks2[tid]
                    if frame_index2 - lost_frame > 150:
                        del track_states2[tid]
                        del lost_tracks2[tid]
                else:
                    del track_states2[tid]
                
        if diff_in_2 > 0 or diff_out_2 > 0:
            count_in_2 += diff_in_2
            count_out_2 += diff_out_2
            if diff_in_2 > 0:
                SystemStatus.add_log(f"📥 CAM 2: Có {diff_in_2} người đi VÀO lối đi sau", "success")
                send_telegram_alert(f"📥 [CAM 2] Có {diff_in_2} người đi vào lối đi sau.", frame2, "counter", "Cam_Cua_Sau")
            if diff_out_2 > 0:
                SystemStatus.add_log(f"📤 CAM 2: Có {diff_out_2} người đi RA lối đi sau", "info")
                send_telegram_alert(f"📤 [CAM 2] Có {diff_out_2} người đi ra lối đi sau.", frame2, "counter", "Cam_Cua_Sau")

        # --- VẼ HÌNH VÀ GHÉP HÌNH ---
        ann1 = frame1.copy()
        if detections1.tracker_id is not None and len(detections1.tracker_id) == len(detections1):
            labels1 = [f"#{tid}" for tid in detections1.tracker_id]
        else: labels1 = [""] * len(detections1)
        ann1 = box_annotator.annotate(scene=ann1, detections=detections1)
        ann1 = label_annotator.annotate(scene=ann1, detections=detections1, labels=labels1)
        cv2.line(ann1, l_out_A_1, l_out_B_1, (0, 165, 255), 2)
        cv2.line(ann1, l_in_A_1, l_in_B_1, (255, 100, 0), 2)
        cv2.putText(ann1, f"CAM 1 | IN: {count_in_1} | OUT: {count_out_1}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        ann2 = frame2.copy()
        if detections2.tracker_id is not None and len(detections2.tracker_id) == len(detections2):
            labels2 = [f"#{tid}" for tid in detections2.tracker_id]
        else: labels2 = [""] * len(detections2)
        ann2 = box_annotator.annotate(scene=ann2, detections=detections2)
        ann2 = label_annotator.annotate(scene=ann2, detections=detections2, labels=labels2)
        cv2.line(ann2, l_out_A_2, l_out_B_2, (0, 165, 255), 2)
        cv2.line(ann2, l_in_A_2, l_in_B_2, (255, 100, 0), 2)
        cv2.putText(ann2, f"CAM 2 | IN: {count_in_2} | OUT: {count_out_2}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Ghép 2 camera song song dạng Side-by-Side
        ann1_res = cv2.resize(ann1, (480, 270))
        ann2_res = cv2.resize(ann2, (480, 270))
        combined_frame = np.hstack((ann1_res, ann2_res))
        
        ret, buffer = cv2.imencode('.jpg', combined_frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["counter"] = round(fps, 1)
        
    cap1.release()
    cap2.release()

# =========================================================================
# LUỒNG 4: LUỒNG PHÁT HIỆN NGÃ (FALL DETECTION)
# =========================================================================
def gen_fall_stream():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[PROCESSORS] [ERROR] Không thể mở webcam cho luồng phát hiện ngã! Sử dụng video làm dự phòng.")
        cap = cv2.VideoCapture("video.mp4")
        if not cap.isOpened():
            return

    print("[PROCESSORS] Khởi tạo thành công luồng phát hiện ngã.")
    fall_counter = 0
    
    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            time.sleep(0.03)
            continue
            
        fall_in_frame = False
        conf_thr = config.settings.get("conf_threshold", 0.25)
        
        # Nhận diện ngã ưu tiên mô hình custom tự train, nếu không sử dụng pose estimation dự phòng
        if yolov8_fall_model is not None:
            results = yolov8_fall_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].cpu().item())
                    conf = float(box.conf[0].cpu().item())
                    
                    if conf > conf_thr:
                        x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                        
                        if cls_id == 0:  # Lớp 0: Người bị Ngã
                            color = (0, 0, 255)
                            label = f"FALL ({conf:.2f})"
                            fall_in_frame = True
                        else:  # Lớp 1: Bình thường
                            color = (0, 255, 0)
                            label = f"Normal ({conf:.2f})"
                            
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        else:
            # Thuật toán dự phòng dựa trên YOLOv8-pose và góc cơ thể
            results = yolov8_pose_model(frame, verbose=False, device=device)
            if len(results) > 0 and results[0].keypoints is not None:
                keypoints_data = results[0].keypoints.data.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                
                for i, kpts in enumerate(keypoints_data):
                    box = boxes[i]
                    x1, y1, x2, y2 = [int(b) for b in box[:4]]
                    w = x2 - x1
                    h = y2 - y1
                    aspect_ratio = w / (h + 1e-5)
                    
                    # Trích xuất các khớp
                    l_sho, r_sho = kpts[5], kpts[6]
                    l_hip, r_hip = kpts[11], kpts[12]
                    
                    has_conf = kpts.shape[1] == 3
                    
                    sho_x = (l_sho[0] + r_sho[0]) / 2
                    sho_y = (l_sho[1] + r_sho[1]) / 2
                    hip_x = (l_hip[0] + r_hip[0]) / 2
                    hip_y = (l_hip[1] + r_hip[1]) / 2
                    
                    sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                    hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0
                    
                    is_horizontal = False
                    if sho_conf > 0.3 and hip_conf > 0.3:
                        dy = sho_y - hip_y
                        dx = sho_x - hip_x
                        angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                        if angle_body < 40 or angle_body > 140:
                            is_horizontal = True
                            
                    # Cảnh báo ngã khi tỉ lệ vàng của khung nằm ngang hoặc góc cơ thể nằm ngang
                    if is_horizontal or aspect_ratio > 1.4:
                        fall_in_frame = True
                        color = (0, 0, 255)
                        label = "FALL (Pose Detection)"
                    else:
                        color = (0, 255, 0)
                        label = "Normal (Pose Detection)"
                        
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 2. Xử lý logic cảnh báo người ngã
        if fall_in_frame:
            fall_counter += 1
            if fall_counter >= 12:  # Báo động khi ngã trên 1.2 giây
                SystemStatus.fall_active = True
                cv2.putText(frame, "CANH BAO: NGUOI NGA!", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                SystemStatus.add_log("⚠️ CẢNH BÁO: Phát hiện người bị ngã hoặc nằm trên sàn!", "danger")
                send_telegram_alert(
                    message="⚠️ [CẢNH BÁO FALL] Cảnh báo nguy hiểm! Phát hiện người bị ngã hoặc nằm yên trên sàn nhà!",
                    frame=frame,
                    alert_type="fall",
                    camera_id="Cam_Phat_Hien_Nga"
                )
        else:
            fall_counter = max(0, fall_counter - 1)
            if fall_counter == 0:
                SystemStatus.fall_active = False

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
               
        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps["fall"] = round(fps, 1)
        
    cap.release()

# =========================================================================
# LUỒNG 5: HỢP NHẤT GIÁM SÁT ĐA KÊNH ĐỘNG (DYNAMIC N-CAMERA STREAM)
# =========================================================================
camera_states = {}
paused_cameras = {}

def pause_camera_alerts(camera_id: str, duration_minutes: int):
    paused_cameras[camera_id] = time.time() + duration_minutes * 60
    print(f"[PROCESSORS] Camera '{camera_id}' alerts paused for {duration_minutes} minutes.")

class CameraState:
    def __init__(self):
        self.track_states = {}
        self.lost_tracks = {}
        self.active_tracks = {}
        self.frame_index = 0
        self.fall_counter = 0
        self.count_in = 0
        self.count_out = 0
        self.last_frame = None
        self.frame_buffer = collections.deque(maxlen=150)
        self.intrusion_entry_times = {}
        self.last_face_log_times = {}

def is_time_in_schedule(start_str, end_str):
    """
    Kiểm tra thời điểm hiện tại có nằm trong lịch trình từ start_str đến end_str hay không.
    Hỗ trợ hoàn hảo cả khung giờ vắt qua ngày hôm sau (Ví dụ: từ 23:00 đêm đến 06:00 sáng).
    """
    if not start_str or not end_str:
        return True
    try:
        from datetime import datetime
        now = datetime.now().time()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        if start_time <= end_time:
            return start_time <= now <= end_time
        else: # Qua đêm, ví dụ: 23:00 - 06:00
            return now >= start_time or now <= end_time
    except Exception:
        return True

def gen_dynamic_stream(camera_id: str):
    """
    Bộ sinh luồng xử lý ảnh camera động.
    Tự động giải quyết các tác vụ deep learning (YOLOv8 Counter, YOLOv5 ROI, MTCNN/FaceNet, YOLOv8-pose Fall)
    dựa trên tính năng (features) được cấu hình động trên Web Dashboard cho camera tương ứng.
    """
    cameras = config.get_cameras_config()
    cfg = next((c for c in cameras if c["camera_id"] == camera_id), None)
    if not cfg:
        print(f"[PROCESSORS] [ERROR] Không tìm thấy cấu hình cho camera: {camera_id}")
        return

    if camera_id not in camera_states:
        camera_states[camera_id] = CameraState()
    state = camera_states[camera_id]

    source = cfg["source"]
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[PROCESSORS] [ERROR] Không thể mở camera source {source} cho camera {camera_id}")
        return

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    db = SessionLocal()
    records = db.query(FaceRecord).all()
    db.close()
    names = [r.name for r in records]
    db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])

    print(f"[PROCESSORS] Bắt đầu khởi chạy luồng dynamic camera: {camera_id}")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            if isinstance(source, str) and os.path.exists(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                state.frame_index = 0
                state.track_states.clear()
                state.lost_tracks.clear()
                state.active_tracks.clear()
                continue
            else:
                time.sleep(0.5)
                continue

        state.frame_index += 1
        frame = cv2.resize(frame, (640, 360))

        if cfg.get("low_light_enhance", False):
            clip_limit = cfg.get("enhance_clip_limit", 2.0)
            try:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l_channel, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
                cl = clahe.apply(l_channel)
                limg = cv2.merge((cl, a, b))
                frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            except Exception as e:
                print(f"[PROCESSORS] Lỗi CLAHE: {e}")

        state.last_frame = frame.copy()

        if state.frame_index % 30 == 0:
            cameras = config.get_cameras_config()
            new_cfg = next((c for c in cameras if c["camera_id"] == camera_id), None)
            if new_cfg:
                cfg = new_cfg
            
            if "face_id" in cfg.get("features", []):
                db = SessionLocal()
                records = db.query(FaceRecord).all()
                db.close()
                names = [r.name for r in records]
                db_embeddings = np.array([json.loads(r.embedding) for r in records]) if records else np.array([])

        features = cfg.get("features", [])
        conf_thr = config.settings.get("conf_threshold", 0.25)
        cooldown_thr = config.settings.get("counter_cooldown", 45)
        alerts_enabled = config.settings.get("alerts_enabled", True)

        is_paused = time.time() < paused_cameras.get(camera_id, 0)

        alert_allowed_by_schedule = True
        if cfg.get("schedule_enabled", False):
            alert_allowed_by_schedule = is_time_in_schedule(cfg.get("schedule_start", "00:00"), cfg.get("schedule_end", "24:00"))

        run_yolo = ("people_counter" in features) or ("intrusion_roi" in features)
        run_face = "face_id" in features
        run_fall = "fall_detection" in features

        detections = None
        if run_yolo:
            results = yolov8_model.track(frame, persist=True, tracker="custom_bytetrack.yaml", conf=conf_thr, classes=[0], verbose=False, device=device)
            detections = sv.Detections.from_ultralytics(results[0])
            detections = detections[detections.class_id == 0]

        annotated_frame = frame.copy()

        if "people_counter" in features and detections is not None:
            lines = cfg.get("lines", [cfg.get("line", [[100, 180], [540, 180]])])
            diff_in = 0
            diff_out = 0
            current_active_tids = set()

            for line_idx, line_pts in enumerate(lines):
                x1, y1 = line_pts[0]
                x2, y2 = line_pts[1]

                dx = x2 - x1
                dy = y2 - y1
                length = math.sqrt(dx*dx + dy*dy)
                if length == 0: length = 1.0
                nx = -dy / length
                ny = dx / length
                d_offset = 20.0

                in_dir = cfg.get("in_direction", "down")
                dot = ny if in_dir == "down" else (-ny if in_dir == "up" else (nx if in_dir == "right" else -nx))

                if dot >= 0:
                    outside_reg = 1
                    inside_reg = 3
                    l_out_A = (int(x1 - d_offset * nx), int(y1 - d_offset * ny))
                    l_out_B = (int(x2 - d_offset * nx), int(y2 - d_offset * ny))
                    l_in_A = (int(x1 + d_offset * nx), int(y1 + d_offset * ny))
                    l_in_B = (int(x2 + d_offset * nx), int(y2 + d_offset * ny))
                else:
                    outside_reg = 3
                    inside_reg = 1
                    l_out_A = (int(x1 + d_offset * nx), int(y1 + d_offset * ny))
                    l_out_B = (int(x2 + d_offset * nx), int(y2 + d_offset * ny))
                    l_in_A = (int(x1 - d_offset * nx), int(y1 - d_offset * ny))
                    l_in_B = (int(x2 - d_offset * nx), int(y2 - d_offset * ny))

                cv2.line(annotated_frame, l_out_A, l_out_B, (0, 165, 255), 2)
                cv2.line(annotated_frame, l_in_A, l_in_B, (255, 100, 0), 2)

                if detections.tracker_id is not None and len(detections.tracker_id) == len(detections):
                    for idx, tid in enumerate(detections.tracker_id):
                        current_active_tids.add(tid)
                        bbox = detections.xyxy[idx]
                        curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                        
                        track_key = f"{tid}_{line_idx}"

                        if track_key not in state.track_states:
                            best_match_tid = None
                            best_match_dist = float('inf')
                            bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                            
                            for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(state.lost_tracks.items()):
                                lost_track_key = f"{lost_tid}_{line_idx}"
                                if lost_tid != tid and state.frame_index - lost_frame < cooldown_thr:
                                    dist = math.dist(curr_bc, lost_pos)
                                    max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (state.frame_index - lost_frame))
                                    if dist < max_dist and dist < best_match_dist:
                                        best_match_tid = lost_tid
                                        best_match_dist = dist
                                        
                            if best_match_tid is not None:
                                lost_track_key = f"{best_match_tid}_{line_idx}"
                                lost_state_tuple, _, _ = state.lost_tracks.get(lost_track_key, (None, None, 0))
                                if lost_state_tuple is not None:
                                    state.track_states[track_key] = lost_state_tuple
                                state.lost_tracks.pop(lost_track_key, None)
                                state.track_states.pop(lost_track_key, None)

                        state.active_tracks[track_key] = curr_bc
                        state.lost_tracks.pop(track_key, None)

                        x_c, y_c = curr_bc
                        v_val = (x_c - x1) * nx + (y_c - y1) * ny
                        region = 1 if v_val < -d_offset else (3 if v_val > d_offset else 2)

                        state_tuple = state.track_states.get(track_key)
                        track_state, last_cross = state_tuple if state_tuple is not None else (None, 0)

                        if region == outside_reg:
                            if track_state == 'from_inside':
                                if state.frame_index - last_cross > cooldown_thr:
                                    diff_out += 1
                                    state.track_states[track_key] = ('from_outside', state.frame_index)
                            else:
                                state.track_states[track_key] = ('from_outside', last_cross)
                        elif region == inside_reg:
                            if track_state == 'from_outside':
                                if state.frame_index - last_cross > cooldown_thr:
                                    diff_in += 1
                                    state.track_states[track_key] = ('from_inside', state.frame_index)
                            else:
                                state.track_states[track_key] = ('from_inside', last_cross)

            for tkey in list(state.active_tracks.keys()):
                parts = tkey.split('_')
                tid_val = int(parts[0])
                if tid_val not in current_active_tids:
                    last_pos = state.active_tracks[tkey]
                    state_tuple = state.track_states.get(tkey)
                    if state_tuple is not None:
                        state.lost_tracks[tkey] = (state_tuple, last_pos, state.frame_index)
                    state.active_tracks.pop(tkey, None)

            for tkey in list(state.track_states.keys()):
                parts = tkey.split('_')
                tid_val = int(parts[0])
                if tid_val not in current_active_tids:
                    if tkey in state.lost_tracks:
                        _, _, lost_frame = state.lost_tracks[tkey]
                        if state.frame_index - lost_frame > 150:
                            state.track_states.pop(tkey, None)
                            state.lost_tracks.pop(tkey, None)
                    else:
                        state.track_states.pop(tkey, None)

            if diff_in > 0 or diff_out > 0:
                state.count_in += diff_in
                state.count_out += diff_out
                if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                    if diff_in > 0:
                        SystemStatus.add_log(f"📥 {camera_id}: Có {diff_in} người đi VÀO", "success")
                        send_telegram_alert(f"📥 [{camera_id}] Có {diff_in} người vừa đi vào.", frame, "counter", camera_id, frame_buffer=list(state.frame_buffer))
                    if diff_out > 0:
                        SystemStatus.add_log(f"📤 {camera_id}: Có {diff_out} người đi RA", "info")
                        send_telegram_alert(f"📤 [{camera_id}] Có {diff_out} người vừa đi ra.", frame, "counter", camera_id, frame_buffer=list(state.frame_buffer))

            labels = [f"#{tid}" for tid in (detections.tracker_id if detections.tracker_id is not None else [])]
            annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
            annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)
            cv2.putText(annotated_frame, f"IN: {state.count_in} | OUT: {state.count_out}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if "intrusion_roi" in features and detections is not None:
            rois = cfg.get("rois", [cfg.get("roi", [[100, 100], [540, 100], [540, 300], [100, 300]])])
            person_in_roi = False
            active_tids_in_roi = set()

            for roi_poly in rois:
                pts = np.array(roi_poly, np.int32).reshape((-1, 1, 2))
                
                is_this_roi_violated = False
                if detections.tracker_id is not None and len(detections.tracker_id) == len(detections):
                    for idx, tid in enumerate(detections.tracker_id):
                        bbox = detections.xyxy[idx]
                        check_points = [
                            (int((bbox[0] + bbox[2]) / 2), int(bbox[3])),
                            (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))
                        ]
                        for cp in check_points:
                            if cv2.pointPolygonTest(pts, cp, False) >= 0:
                                person_in_roi = True
                                is_this_roi_violated = True
                                active_tids_in_roi.add(tid)
                                break
                else:
                    for bbox in detections.xyxy:
                        check_points = [
                            (int((bbox[0] + bbox[2]) / 2), int(bbox[3])),
                            (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))
                        ]
                        for cp in check_points:
                            if cv2.pointPolygonTest(pts, cp, False) >= 0:
                                person_in_roi = True
                                is_this_roi_violated = True
                                break

                color = (0, 0, 255) if is_this_roi_violated else (0, 255, 255)
                cv2.polylines(annotated_frame, [pts], True, color, 2)

            loitering_detected = False
            current_time = time.time()
            loitering_threshold = config.settings.get("loitering_threshold", 10)

            for tid in active_tids_in_roi:
                if tid not in state.intrusion_entry_times:
                    state.intrusion_entry_times[tid] = current_time
                else:
                    elapsed = current_time - state.intrusion_entry_times[tid]
                    if elapsed > loitering_threshold:
                        loitering_detected = True
                        cv2.putText(annotated_frame, f"LẢNG VẢNG ID #{tid}: {int(elapsed)}s", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                        
                        if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                            SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện lảng vảng ID #{tid} quá {loitering_threshold} giây!", "danger")
                            send_telegram_alert(
                                message=f"⚠️ [{camera_id}] Phát hiện người lảng vảng ID #{tid} ở lại vùng cấm {int(elapsed)} giây!",
                                frame=frame,
                                alert_type="intrusion",
                                camera_id=camera_id,
                                frame_buffer=list(state.frame_buffer)
                            )

            for tid in list(state.intrusion_entry_times.keys()):
                if tid not in active_tids_in_roi:
                    state.intrusion_entry_times.pop(tid, None)

            if person_in_roi:
                SystemStatus.intrusion_active = True
                if not loitering_detected:
                    cv2.putText(annotated_frame, "CANH BAO XAM NHAP!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                        SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện xâm nhập vùng cấm!", "danger")
                        send_telegram_alert(
                            message=f"⚠️ [{camera_id}] Phát hiện người xâm nhập vùng cấm!",
                            frame=frame,
                            alert_type="intrusion",
                            camera_id=camera_id,
                            frame_buffer=list(state.frame_buffer)
                        )
            else:
                SystemStatus.intrusion_active = False

        if run_face:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            boxes, _ = mtcnn_multi.detect(img_pil)
            if boxes is not None:
                faces = mtcnn_multi(img_pil)
                if faces is not None:
                    embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                    face_log_cooldown = config.settings.get("face_log_cooldown", 30)
                    current_time = time.time()
                    
                    for box, emb in zip(boxes, embeddings):
                        x_1, y_1, x_2, y_2 = [int(b) for b in box]
                        best_match_name = "Unknown"
                        best_distance = float("inf")
                        if len(db_embeddings) > 0:
                            distances = np.linalg.norm(db_embeddings - emb, axis=1)
                            min_idx = np.argmin(distances)
                            min_dist = distances[min_idx]
                            if min_dist < 0.8:
                                best_match_name = names[min_idx]
                                best_distance = min_dist

                        color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                        cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                        text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                        cv2.putText(annotated_frame, text, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                        last_log_time = state.last_face_log_times.get(best_match_name, 0)
                        if current_time - last_log_time > face_log_cooldown:
                            state.last_face_log_times[best_match_name] = current_time
                            
                            if best_match_name == "Unknown":
                                if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                    SystemStatus.add_log(f"⚠️ {camera_id}: Phát hiện khuôn mặt lạ!", "danger")
                                    send_telegram_alert(
                                        message=f"⚠️ [{camera_id}] Phát hiện khuôn mặt lạ xuất hiện!",
                                        frame=frame,
                                        alert_type="face",
                                        camera_id=camera_id,
                                        frame_buffer=list(state.frame_buffer),
                                        face_name="Unknown"
                                    )
                            else:
                                if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                                    SystemStatus.add_log(f"👤 {camera_id}: Nhận diện thành công khuôn mặt: {best_match_name}", "info")
                                    send_telegram_alert(
                                        message=f"👤 [{camera_id}] Nhận diện thành công khuôn mặt: {best_match_name}",
                                        frame=frame,
                                        alert_type="face",
                                        camera_id=camera_id,
                                        frame_buffer=list(state.frame_buffer),
                                        face_name=best_match_name
                                    )

        if run_fall:
            fall_in_frame = False
            if yolov8_fall_model is not None:
                results = yolov8_fall_model(frame, verbose=False, device=device)
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].cpu().item())
                        conf = float(box.conf[0].cpu().item())
                        if conf > conf_thr:
                            x_1, y_1, x_2, y_2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                            if cls_id == 0:
                                fall_in_frame = True
                                color = (0, 0, 255)
                                label = f"FALL ({conf:.2f})"
                            else:
                                color = (0, 255, 0)
                                label = f"Normal ({conf:.2f})"
                            cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                            cv2.putText(annotated_frame, label, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            else:
                results = yolov8_pose_model(frame, verbose=False, device=device)
                if len(results) > 0 and results[0].keypoints is not None:
                    keypoints_data = results[0].keypoints.data.cpu().numpy()
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    for i, kpts in enumerate(keypoints_data):
                        box = boxes[i]
                        x_1, y_1, x_2, y_2 = [int(b) for b in box[:4]]
                        w = x_2 - x_1
                        h = y_2 - y_1
                        aspect_ratio = w / (h + 1e-5)

                        l_sho, r_sho = kpts[5], kpts[6]
                        l_hip, r_hip = kpts[11], kpts[12]
                        has_conf = kpts.shape[1] == 3

                        sho_x = (l_sho[0] + r_sho[0]) / 2
                        sho_y = (l_sho[1] + r_sho[1]) / 2
                        hip_x = (l_hip[0] + r_hip[0]) / 2
                        hip_y = (l_hip[1] + r_hip[1]) / 2

                        sho_conf = min(l_sho[2], r_sho[2]) if has_conf else 1.0
                        hip_conf = min(l_hip[2], r_hip[2]) if has_conf else 1.0

                        is_horizontal = False
                        if sho_conf > 0.3 and hip_conf > 0.3:
                            dy = sho_y - hip_y
                            dx = sho_x - hip_x
                            angle_body = abs(np.arctan2(dy, dx) * 180 / np.pi)
                            if angle_body < 40 or angle_body > 140:
                                is_horizontal = True

                        if is_horizontal or aspect_ratio > 1.4:
                            fall_in_frame = True
                            color = (0, 0, 255)
                            label = "FALL (Pose)"
                        else:
                            color = (0, 255, 0)
                            label = "Normal (Pose)"
                        cv2.rectangle(annotated_frame, (x_1, y_1), (x_2, y_2), color, 2)
                        cv2.putText(annotated_frame, label, (x_1, y_1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if fall_in_frame:
                state.fall_counter += 1
                if state.fall_counter >= 12:
                    SystemStatus.fall_active = True
                    cv2.putText(annotated_frame, "PHÁT HIỆN NGÃ!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if alerts_enabled and alert_allowed_by_schedule and not is_paused:
                        SystemStatus.add_log(f"🚨 {camera_id}: Phát hiện người bị ngã!", "danger")
                        send_telegram_alert(
                            message=f"🚨 [{camera_id}] Phát hiện có người bị ngã!",
                            frame=frame,
                            alert_type="fall",
                            camera_id=camera_id,
                            frame_buffer=list(state.frame_buffer)
                        )
            else:
                state.fall_counter = max(0, state.fall_counter - 1)

        # Trạng thái lịch trình
        if not alert_allowed_by_schedule:
            cv2.putText(annotated_frame, "Cảnh báo tắt (Theo Lịch Trình)", (10, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        ret_enc, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret_enc: continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        t_end = time.time()
        fps = 1.0 / (t_end - t_start + 1e-6)
        camera_fps[camera_id] = round(fps, 1)

    cap.release()
