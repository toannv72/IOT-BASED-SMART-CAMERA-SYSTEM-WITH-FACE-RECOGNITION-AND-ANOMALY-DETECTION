import cv2
import json
import threading
import queue
import time
import torch
import supervision as sv
from ultralytics import YOLO

# --- GENERAL SETTINGS ---
CONFIG_FILE = "cameras_config.json"
MODEL_PATH = "yolov8s.pt"

# Global states
TOTAL_INSIDE = 0
total_lock = threading.Lock()

def save_config_file(camera_id, p1, p2):
    try:
        with open(CONFIG_FILE, "r") as f:
            cameras = json.load(f)
        for cam in cameras:
            if cam["camera_id"] == camera_id:
                cam["line"] = [list(p1), list(p2)]
                break
        with open(CONFIG_FILE, "w") as f:
            json.dump(cameras, f, indent=4)
        print(f"[SYSTEM] Configuration updated in {CONFIG_FILE} for camera {camera_id}.")
    except Exception as e:
        print(f"[ERROR] Failed to save configuration: {e}")

class LineDrawer:
    def __init__(self, cam_processor, scale_x, scale_y):
        self.cam_processor = cam_processor
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.temp_point = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Map click coordinates from 640x480 display size to original frame size
            orig_x = int(x * self.scale_x)
            orig_y = int(y * self.scale_y)
            
            if self.temp_point is None:
                self.temp_point = (orig_x, orig_y)
                print(f"[{self.cam_processor.cam_id}] First point set at {self.temp_point}. Click again to set second point.")
            else:
                p2 = (orig_x, orig_y)
                p1 = self.temp_point
                self.cam_processor.line_A = p1
                self.cam_processor.line_B = p2
                self.cam_processor.update_line_zone() # Update line zone object
                self.temp_point = None
                print(f"[{self.cam_processor.cam_id}] Line updated: {p1} -> {p2}")
                save_config_file(self.cam_processor.cam_id, p1, p2)

class CameraProcessor(threading.Thread):
    def __init__(self, cam_config, frame_queue):
        super().__init__()
        self.cam_id = cam_config["camera_id"]
        self.source = cam_config["source"]
        self.line_A = tuple(cam_config["line"][0])
        self.line_B = tuple(cam_config["line"][1])
        self.in_direction = cam_config.get("in_direction", "down")
        self.frame_queue = frame_queue
        self.running = True
        
        self.count_in = 0
        self.count_out = 0
        
        self.update_line_zone()
        
        # Load model
        print(f"[{self.cam_id}] Loading YOLOv8 model...")
        self.model = YOLO(MODEL_PATH)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[{self.cam_id}] Running on device: {self.device}")
        
    def update_line_zone(self):
        import math
        x1, y1 = self.line_A
        x2, y2 = self.line_B
        
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            length = 1.0
            
        # Normal perpendicular unit vector
        self.nx = -dy / length
        self.ny = dx / length
        
        # Parallel lines distance offset (30 pixels)
        d = 30.0
        
        # Determine inside/outside regions based on in_direction
        in_dir = self.in_direction
        if in_dir == "down":
            dot = self.ny
        elif in_dir == "up":
            dot = -self.ny
        elif in_dir == "right":
            dot = self.nx
        elif in_dir == "left":
            dot = -self.nx
        else:
            dot = 1.0
            
        if dot >= 0:
            # Region 3 (+normal) is INSIDE, Region 1 (-normal) is OUTSIDE
            self.outside_reg = 1
            self.inside_reg = 3
            self.line_outer_A = (int(x1 - d * self.nx), int(y1 - d * self.ny))
            self.line_outer_B = (int(x2 - d * self.nx), int(y2 - d * self.ny))
            self.line_inner_A = (int(x1 + d * self.nx), int(y1 + d * self.ny))
            self.line_inner_B = (int(x2 + d * self.nx), int(y2 + d * self.ny))
        else:
            # Region 1 (-normal) is INSIDE, Region 3 (+normal) is OUTSIDE
            self.outside_reg = 3
            self.inside_reg = 1
            self.line_outer_A = (int(x1 + d * self.nx), int(y1 + d * self.ny))
            self.line_outer_B = (int(x2 + d * self.nx), int(y2 + d * self.ny))
            self.line_inner_A = (int(x1 - d * self.nx), int(y1 - d * self.ny))
            self.line_inner_B = (int(x2 - d * self.nx), int(y2 - d * self.ny))
            
        # Double-line crossing tracking states
        self.track_states = {}    # tid -> 'from_outside' | 'from_inside'
        self.lost_tracks = {}     # tid -> (state, last_pos, frame_index)
        self.active_tracks = {}    # tid -> bottom_center_pt
        self.frame_index = 0

    def process_tracking(self, results):
        global TOTAL_INSIDE
        self.frame_index += 1
        import math
        
        # Convert ultralytics results to supervision Detections
        detections = sv.Detections.from_ultralytics(results[0])
        
        # Filter detections for person class only (class 0)
        detections = detections[detections.class_id == 0]
        
        diff_in = 0
        diff_out = 0
        
        x1, y1 = self.line_A
        nx, ny = self.nx, self.ny
        d = 30.0
        outside_reg = self.outside_reg
        inside_reg = self.inside_reg
        
        current_active_tids = set()
        
        if detections.tracker_id is not None and len(detections.tracker_id) == len(detections):
            for i, tid in enumerate(detections.tracker_id):
                current_active_tids.add(tid)
                bbox = detections.xyxy[i]
                curr_bc = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
                
                # 1. Inherit state if this track is newly detected and close to a lost track
                if tid not in self.track_states:
                    best_match_tid = None
                    best_match_dist = float('inf')
                    bbox_dim = max(bbox[2]-bbox[0], bbox[3]-bbox[1])
                    for lost_tid, (lost_state_tuple, lost_pos, lost_frame) in list(self.lost_tracks.items()):
                        # Only inherit from a different lost ID since same ID is naturally preserved in self.track_states
                        if lost_tid != tid and self.frame_index - lost_frame < 45:
                            dist = math.dist(curr_bc, lost_pos)
                            max_dist = min(150.0, 0.5 * bbox_dim + 3.5 * (self.frame_index - lost_frame))
                            if dist < max_dist and dist < best_match_dist:
                                best_match_tid = lost_tid
                                best_match_dist = dist
                    if best_match_tid is not None:
                        lost_state_tuple, _, _ = self.lost_tracks[best_match_tid]
                        if lost_state_tuple is not None:
                            self.track_states[tid] = lost_state_tuple
                            print(f"[{self.cam_id}] [TRACK INHERIT] New ID #{tid} inherited state {lost_state_tuple} from lost ID #{best_match_tid} (dist: {best_match_dist:.1f}px)")
                        if best_match_tid in self.lost_tracks:
                            del self.lost_tracks[best_match_tid]
                        if best_match_tid in self.track_states:
                            del self.track_states[best_match_tid]
                
                # Update current active position and clear from lost_tracks if it returned
                self.active_tracks[tid] = curr_bc
                if tid in self.lost_tracks:
                    del self.lost_tracks[tid]
                
                # 2. Compute project coordinate v and classify region
                x, y = curr_bc
                v = (x - x1) * nx + (y - y1) * ny
                
                if v < -d:
                    region = 1
                elif v > d:
                    region = 3
                else:
                    region = 2
                    
                # 3. State machine with Cooldown
                state_tuple = self.track_states.get(tid)
                if state_tuple is not None:
                    state, last_cross = state_tuple
                else:
                    state, last_cross = None, 0
                    
                if region == outside_reg:
                    if state == 'from_inside':
                        if self.frame_index - last_cross > 45:
                            diff_out += 1
                            self.track_states[tid] = ('from_outside', self.frame_index)
                            print(f"[{self.cam_id}] ID #{tid} completed crossing: INSIDE -> OUTSIDE. Counted OUT.")
                    else:
                        self.track_states[tid] = ('from_outside', last_cross)
                elif region == inside_reg:
                    if state == 'from_outside':
                        if self.frame_index - last_cross > 45:
                            diff_in += 1
                            self.track_states[tid] = ('from_inside', self.frame_index)
                            print(f"[{self.cam_id}] ID #{tid} completed crossing: OUTSIDE -> INSIDE. Counted IN.")
                    else:
                        self.track_states[tid] = ('from_inside', last_cross)
                    
        # 4. Clean up lost tracks and store them for split tracking (DO NOT delete from track_states immediately)
        for tid in list(self.active_tracks.keys()):
            if tid not in current_active_tids:
                last_pos = self.active_tracks[tid]
                state_tuple = self.track_states.get(tid)
                if state_tuple is not None:
                    self.lost_tracks[tid] = (state_tuple, last_pos, self.frame_index)
                del self.active_tracks[tid]
                    
        # 5. Clean up stale states and lost tracks to avoid memory leaks
        for tid in list(self.track_states.keys()):
            if tid not in current_active_tids:
                if tid in self.lost_tracks:
                    state_tuple, pos, lost_frame = self.lost_tracks[tid]
                    if self.frame_index - lost_frame > 150:
                        del self.track_states[tid]
                        del self.lost_tracks[tid]
                else:
                    del self.track_states[tid]
                
        # Apply count to local and global totals
        if diff_in > 0 or diff_out > 0:
            self.count_in += diff_in
            self.count_out += diff_out
            with total_lock:
                TOTAL_INSIDE += (diff_in - diff_out)
            print(f"[{self.cam_id}] Crossing detected! IN: +{diff_in}, OUT: +{diff_out} | Total IN: {self.count_in}, OUT: {self.count_out} | Total Inside: {TOTAL_INSIDE}")

    def run(self):
        source = self.source
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"[{self.cam_id}] ERROR: Cannot open source {source}")
            self.running = False
            return
            
        print(f"[{self.cam_id}] Stream started.")
        
        # Annotators from supervision
        box_annotator = sv.BoxAnnotator()
        label_annotator = sv.LabelAnnotator()
        line_annotator = sv.LineZoneAnnotator(thickness=2, text_thickness=2, text_scale=1.0)
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                # Re-initialize line zone to reset internal crossing memory on loop
                self.update_line_zone()
                continue

            # Run person tracker (using persist=True) and custom ByteTrack configuration
            results = self.model.track(frame, persist=True, tracker="custom_bytetrack.yaml", conf=0.25, classes=[0], verbose=False, device=self.device)
            
            # Process tracking using supervision
            self.process_tracking(results)

            # Draw boxes, tracker labels, and the line zone
            detections = sv.Detections.from_ultralytics(results[0])
            detections = detections[detections.class_id == 0]
            
            # Format labels with track ids
            if detections.tracker_id is not None and len(detections.tracker_id) == len(detections):
                labels = [f"#{tid}" for tid in detections.tracker_id]
            else:
                labels = ["" for _ in range(len(detections))]
            
            annotated_frame = frame.copy()
            annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
            annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)
            
            # Draw Line 1 (Outer - Orange)
            cv2.line(annotated_frame, self.line_outer_A, self.line_outer_B, (0, 165, 255), 2)
            cv2.putText(annotated_frame, "Vach Ngoai (OUTER)", (self.line_outer_A[0], self.line_outer_A[1] - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
            
            # Draw Line 2 (Inner - Teal/Blue)
            cv2.line(annotated_frame, self.line_inner_A, self.line_inner_B, (255, 100, 0), 2)
            cv2.putText(annotated_frame, "Vach Trong (INNER)", (self.line_inner_A[0], self.line_inner_A[1] - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)
            
            # Draw local count text
            text = f"IN: {self.count_in} | OUT: {self.count_out}"
            cv2.putText(annotated_frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Send to queue for main thread display
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put((self.cam_id, annotated_frame))
            
            time.sleep(0.01)
            
        cap.release()

def main():
    with open(CONFIG_FILE, "r") as f:
        cameras = json.load(f)

    frame_queues = {}
    threads = []
    
    for cam in cameras:
        q = queue.Queue(maxsize=2)
        frame_queues[cam["camera_id"]] = q
        t = CameraProcessor(cam, q)
        t.start()
        threads.append(t)

    print("==================================================")
    print("PEOPLE COUNTER RUNNING (SUPERVISION). Press 'q' to quit.")
    print("Left-click on camera windows to draw a new counting line.")
    print("==================================================")
    
    drawers = {}
    
    try:
        while True:
            for cam_id, q in frame_queues.items():
                if not q.empty():
                    cam_id_q, frame = q.get()
                    
                    # Compute scaling parameters when window displays
                    if cam_id not in drawers:
                        processor = None
                        for t in threads:
                            if t.cam_id == cam_id:
                                processor = t
                                break
                        
                        orig_h, orig_w = frame.shape[:2]
                        scale_x = orig_w / 640.0
                        scale_y = orig_h / 480.0
                        
                        cv2.namedWindow(cam_id)
                        drawer = LineDrawer(processor, scale_x, scale_y)
                        cv2.setMouseCallback(cam_id, drawer.mouse_callback)
                        drawers[cam_id] = drawer
                    
                    # Resize frame for screen display
                    display_frame = cv2.resize(frame, (640, 480))
                    
                    # Draw overall TOTAL HOUSE overlay
                    with total_lock:
                        cv2.putText(display_frame, f"TOTAL INSIDE: {TOTAL_INSIDE}", (10, 80), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    # Visual feedback if first point of line is set
                    drawer = drawers.get(cam_id)
                    if drawer and drawer.temp_point is not None:
                        # Map original temp point back to display coordinates
                        tx = int(drawer.temp_point[0] / drawer.scale_x)
                        ty = int(drawer.temp_point[1] / drawer.scale_y)
                        cv2.circle(display_frame, (tx, ty), 6, (0, 0, 255), -1)
                        cv2.putText(display_frame, "Click again to finish line", (tx + 10, ty - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                                    
                    cv2.imshow(cam_id, display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("Cleaning up and stopping threads...")
        for t in threads:
            t.running = False
        for t in threads:
            t.join()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
