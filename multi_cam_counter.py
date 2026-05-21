import cv2
import json
import threading
import queue
import time
from ultralytics import YOLO

# --- CÀI ĐẶT CHUNG ---
CONFIG_FILE = "cameras_config.json"
MODEL_PATH = "yolov8n.pt" # Dùng bản nano cho nhẹ khi chạy đa luồng

# Biến dùng chung toàn hệ thống
TOTAL_INSIDE = 0
total_lock = threading.Lock()

def check_intersect(A, B, C, D):
    # Kiểm tra xem đoạn thẳng AB có cắt đoạn CD không
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

class CameraProcessor(threading.Thread):
    def __init__(self, cam_config, frame_queue):
        super().__init__()
        self.cam_id = cam_config["camera_id"]
        self.source = cam_config["source"]
        self.line_A = tuple(cam_config["line"][0])
        self.line_B = tuple(cam_config["line"][1])
        self.in_direction = cam_config["in_direction"] 
        self.frame_queue = frame_queue
        self.running = True
        
        self.count_in = 0
        self.count_out = 0
        self.track_history = {} # ID -> tâm (x, y) trước đó
        
        # Load model riêng cho từng luồng để tránh xung đột
        print(f"[{self.cam_id}] Đang tải model YOLOv8...")
        self.model = YOLO(MODEL_PATH)
        
    def get_in_vector(self):
        if self.in_direction == "down": return (0, 1)
        if self.in_direction == "up": return (0, -1)
        if self.in_direction == "left": return (-1, 0)
        if self.in_direction == "right": return (1, 0)
        return (0, 1)

    def process_tracking(self, results):
        global TOTAL_INSIDE
        
        # Nếu không phát hiện đối tượng nào
        if results[0].boxes.id is None:
            return

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        classes = results[0].boxes.cls.int().cpu().tolist()

        in_vec = self.get_in_vector()

        for box, track_id, cls in zip(boxes, track_ids, classes):
            if cls != 0: continue # Chỉ quan tâm người (class 0)
            
            x1, y1, x2, y2 = box
            cx, cy = int((x1 + x2) / 2), int(y2) # Lấy điểm dưới cùng (bàn chân)
            curr_pt = (cx, cy)
            
            if track_id in self.track_history:
                prev_pt = self.track_history[track_id]
                
                # Kiểm tra giao cắt giữa đường di chuyển và vạch kẻ
                if check_intersect(self.line_A, self.line_B, prev_pt, curr_pt):
                    # Tính hướng đi bằng Dot Product
                    move_vec = (curr_pt[0] - prev_pt[0], curr_pt[1] - prev_pt[1])
                    dot_product = move_vec[0] * in_vec[0] + move_vec[1] * in_vec[1]
                    
                    if dot_product > 0:
                        self.count_in += 1
                        with total_lock: TOTAL_INSIDE += 1
                        print(f"[{self.cam_id}] IN! Total: {TOTAL_INSIDE}")
                    else:
                        self.count_out += 1
                        with total_lock: TOTAL_INSIDE -= 1
                        print(f"[{self.cam_id}] OUT! Total: {TOTAL_INSIDE}")
                        
            self.track_history[track_id] = curr_pt

    def run(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"[{self.cam_id}] LỖI: Không thể mở camera/video {self.source}")
            self.running = False
            return
            
        print(f"[{self.cam_id}] Bắt đầu xử lý luồng...")
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print(f"[{self.cam_id}] Đã hết video hoặc mất kết nối. Đang lặp lại (test)...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.track_history.clear() # Xóa lịch sử khi lặp lại
                continue

            # Tracking người
            results = self.model.track(frame, persist=True, classes=[0], verbose=False)
            
            self.process_tracking(results)

            # Vẽ UI
            annotated_frame = results[0].plot()
            cv2.line(annotated_frame, self.line_A, self.line_B, (0, 255, 255), 3)
            
            # Text hiển thị
            text = f"IN: {self.count_in} | OUT: {self.count_out}"
            cv2.putText(annotated_frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Gửi frame cho Main Thread để hiển thị
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait() # Bỏ frame cũ nếu quá đầy
                except queue.Empty:
                    pass
            self.frame_queue.put((self.cam_id, annotated_frame))
            
            time.sleep(0.01) # Nhường CPU một chút
            
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

    print("Hệ thống đã khởi động. Nhấn 'q' để thoát.")
    
    try:
        while True:
            # Hiển thị tất cả camera
            for cam_id, q in frame_queues.items():
                if not q.empty():
                    frame = q.get()
                    
                    # Vẽ thêm TOTAL INSIDE chung
                    with total_lock:
                        cv2.putText(frame[1], f"TOTAL HOUSE: {TOTAL_INSIDE}", (10, 80), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                                    
                    # Thu nhỏ khung hình để có thể xem 2 camera trên 1 màn hình
                    display_frame = cv2.resize(frame[1], (640, 480))
                    cv2.imshow(cam_id, display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("Đang dọn dẹp hệ thống...")
        for t in threads:
            t.running = False
        for t in threads:
            t.join()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
