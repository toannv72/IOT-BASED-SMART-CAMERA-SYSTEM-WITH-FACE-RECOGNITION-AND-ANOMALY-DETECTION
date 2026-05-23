import os
import cv2
import random
import glob
import re

def parse_annotation_line(line):
    # Format usually: frame_num fall_flag x_min y_min x_max y_max
    # or separated by commas/whitespace. Let's make it robust.
    parts = re.split(r'[\s,]+', line.strip())
    if len(parts) >= 6:
        try:
            frame_num = int(parts[0])
            fall_flag = int(parts[1])
            x_min = int(parts[2])
            y_min = int(parts[3])
            x_max = int(parts[4])
            y_max = int(parts[5])
            return frame_num, fall_flag, x_min, y_min, x_max, y_max
        except ValueError:
            return None
    return None

def preprocess(dataset_dir, output_dir):
    print(f"[PREPROCESS] Starting preprocessing from: {dataset_dir}")
    print(f"[PREPROCESS] Output directory: {output_dir}")
    
    # Định nghĩa thư mục train/val
    train_img_dir = os.path.join(output_dir, "train", "images")
    train_lbl_dir = os.path.join(output_dir, "train", "labels")
    val_img_dir = os.path.join(output_dir, "val", "images")
    val_lbl_dir = os.path.join(output_dir, "val", "labels")
    
    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)
        
    # Tìm tất cả video
    # Dataset Le2i chứa các thư mục: Home, Coffee_room, Office, Lecture_room
    video_paths = []
    for ext in ['*.avi', '*.mp4', '*.mkv']:
        video_paths.extend(glob.glob(os.path.join(dataset_dir, "**", ext), recursive=True))
        
    print(f"[PREPROCESS] Found {len(video_paths)} videos.")
    
    # Chia train/val theo video (Tránh rò rỉ dữ liệu giữa các frame kề nhau)
    random.seed(42)
    random.shuffle(video_paths)
    split_idx = int(len(video_paths) * 0.8)
    train_videos = video_paths[:split_idx]
    val_videos = video_paths[split_idx:]
    
    print(f"[PREPROCESS] Split: {len(train_videos)} train videos, {len(val_videos)} val videos.")
    
    # Hàm xử lý danh sách video
    def process_video_list(videos, img_out, lbl_out, dataset_type):
        extracted_count = 0
        fall_count = 0
        normal_count = 0
        
        for idx, v_path in enumerate(videos):
            v_name = os.path.splitext(os.path.basename(v_path))[0]
            v_dir = os.path.dirname(v_path)
            
            # Tìm file annotation tương ứng
            # Thường nằm trong thư mục 'Annotation_files' hoặc cùng thư mục video
            ann_name = v_name + ".txt"
            ann_path = None
            
            # Tìm kiếm file annotation
            possible_ann_paths = [
                os.path.join(v_dir, ann_name),
                os.path.join(v_dir, "Annotation_files", ann_name),
                os.path.join(os.path.dirname(v_dir), "Annotation_files", ann_name)
            ]
            
            for p in possible_ann_paths:
                if os.path.exists(p):
                    ann_path = p
                    break
                    
            if not ann_path:
                # Tìm kiếm quét rộng hơn
                found = glob.glob(os.path.join(dataset_dir, "**", ann_name), recursive=True)
                if found:
                    ann_path = found[0]
                    
            if not ann_path:
                print(f"[{dataset_type}] Skipped video {v_name}: annotation file not found.")
                continue
                
            # Đọc annotation
            annotations = {}
            with open(ann_path, 'r') as f:
                for line in f:
                    parsed = parse_annotation_line(line)
                    if parsed:
                        frame_num, fall_flag, x_min, y_min, x_max, y_max = parsed
                        annotations[frame_num] = (fall_flag, x_min, y_min, x_max, y_max)
                        
            if not annotations:
                print(f"[{dataset_type}] Skipped video {v_name}: annotation file empty or malformed.")
                continue
                
            # Mở video
            cap = cv2.VideoCapture(v_path)
            if not cap.isOpened():
                print(f"[{dataset_type}] Cannot open video: {v_path}")
                continue
                
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_idx += 1
                
                # Check nếu frame có annotation
                if frame_idx in annotations:
                    fall_flag, x_min, y_min, x_max, y_max = annotations[frame_idx]
                    
                    # Bỏ qua nếu tọa độ không hợp lệ hoặc người ở ngoài khung hình
                    if x_min >= x_max or y_min >= y_max or x_max <= 0 or y_max <= 0:
                        continue
                        
                    # Xác định nhãn
                    # 0: bình thường, 1: đang ngã, 2: nằm sàn
                    is_fall = fall_flag in [1, 2]
                    class_id = 1 if is_fall else 0
                    
                    # Trích xuất có chọn lọc:
                    # - Nếu là NGÃ: Lấy toàn bộ frame để tối đa dữ liệu ngã quý giá.
                    # - Nếu là BÌNH THƯỜNG: Chỉ lấy 1 frame mỗi giây (khoảng 25-30 frames) để tránh dư thừa.
                    if not is_fall and frame_idx % 25 != 0:
                        continue
                        
                    h_img, w_img = frame.shape[:2]
                    
                    # Chuẩn hóa tọa độ YOLO (x_center, y_center, width, height) tỷ lệ [0, 1]
                    w_box = x_max - x_min
                    h_box = y_max - y_min
                    x_center = x_min + w_box / 2.0
                    y_center = y_min + h_box / 2.0
                    
                    x_center_norm = x_center / w_img
                    y_center_norm = y_center / h_img
                    w_norm = w_box / w_img
                    h_norm = h_box / h_img
                    
                    # Ràng buộc giá trị trong khoảng [0, 1]
                    x_center_norm = max(0.0, min(1.0, x_center_norm))
                    y_center_norm = max(0.0, min(1.0, y_center_norm))
                    w_norm = max(0.0, min(1.0, w_norm))
                    h_norm = max(0.0, min(1.0, h_norm))
                    
                    # Đặt tên file xuất
                    out_name = f"{v_name}_f{frame_idx}"
                    out_img_path = os.path.join(img_out, out_name + ".jpg")
                    out_lbl_path = os.path.join(lbl_out, out_name + ".txt")
                    
                    # Ghi ảnh
                    cv2.imwrite(out_img_path, frame)
                    
                    # Ghi nhãn YOLO
                    with open(out_lbl_path, 'w') as lf:
                        lf.write(f"{class_id} {x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                        
                    extracted_count += 1
                    if is_fall:
                        fall_count += 1
                    else:
                        normal_count += 1
                        
            cap.release()
            if (idx + 1) % 10 == 0 or (idx + 1) == len(videos):
                print(f"[{dataset_type}] Processed {idx+1}/{len(videos)} videos. Extracted {extracted_count} frames ({fall_count} fall, {normal_count} normal).")
                
    # Chạy tiền xử lý
    process_video_list(train_videos, train_img_dir, train_lbl_dir, "TRAIN")
    process_video_list(val_videos, val_img_dir, val_lbl_dir, "VAL")
    
    # Tạo file data.yaml
    yaml_content = f"""train: {os.path.abspath(os.path.join(output_dir, 'train', 'images'))}
val: {os.path.abspath(os.path.join(output_dir, 'val', 'images'))}

nc: 2
names:
  0: normal
  1: fall
"""
    with open(os.path.join(output_dir, "data.yaml"), "w") as yf:
        yf.write(yaml_content)
    print("[PREPROCESS] Successfully created data.yaml config file.")

if __name__ == "__main__":
    # Tìm kiếm cache path của Kagglehub trên ổ D
    # Ví dụ: d:\CODE\yolo\kaggle_cache\datasets\tuyenldvn\falldataset-imvia\versions\*
    import glob
    cache_pattern = r"d:\CODE\yolo\kaggle_cache\datasets\tuyenldvn\falldataset-imvia\versions\*"
    cache_folders = glob.glob(cache_pattern)
    
    if cache_folders:
        # Lấy thư mục mới nhất
        dataset_dir = sorted(cache_folders)[-1]
        output_dir = "d:\\CODE\\yolo\\dataset"
        preprocess(dataset_dir, output_dir)
    else:
        print("[PREPROCESS] Downloaded dataset folder not found in Kaggle cache on D drive!")
