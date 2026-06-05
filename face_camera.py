import cv2
import requests
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image

API_URL_EMBEDDINGS = "http://localhost:8000/embeddings"
THRESHOLD = 0.8 

def load_registered_faces():
    print("Đang tải cơ sở dữ liệu khuôn mặt từ API...")
    try:
        response = requests.get(API_URL_EMBEDDINGS)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return [], []
                
            names = []
            embeddings = []
            for person in data:
                names.append(person["name"])
                embeddings.append(person["embedding"])
                
            # Tối ưu: Chuyển toàn bộ danh sách embedding thành 1 Ma trận Numpy (N x 512)
            # Giúp tính toán khoảng cách hàng loạt bằng C/C++ ngầm dưới Numpy cực nhanh
            db_embeddings = np.array(embeddings)
            
            print(f"Đã tải thành công {len(data)} khuôn mặt.")
            return names, db_embeddings
        else:
            print("Lỗi từ API:", response.text)
            return [], []
    except Exception as e:
        print("Lỗi kết nối API. Hãy chắc chắn 'face_api.py' đang chạy.")
        return [], []

def main():
    # Tối ưu: Tự động chạy trên GPU (CUDA) nếu có, nếu không thì CPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Khởi tạo FaceNet trên {device}...")
    mtcnn = MTCNN(keep_all=True, thresholds=[0.5, 0.6, 0.6], device=device) 
    resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    names, db_embeddings = load_registered_faces()

    import sys
    if sys.platform.startswith('win'):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Không thể mở webcam!")
        return

    print("--- BẮT ĐẦU NHẬN DIỆN KHUÔN MẶT ---")
    print("Nhấn 'q' để thoát, 'r' để tải lại danh sách từ DB.")

    while True:
        ret, frame = cap.read()
        if not ret: break
            
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        boxes, _ = mtcnn.detect(img)
        
        if boxes is not None:
            faces = mtcnn(img)
            if faces is not None:
                # Tối ưu: Xử lý inference 1 lần cho TẤT CẢ khuôn mặt (Batch Processing)
                embeddings = resnet(faces.to(device)).detach().cpu().numpy()
                
                for i, (box, emb) in enumerate(zip(boxes, embeddings)):
                    x1, y1, x2, y2 = [int(b) for b in box]
                    
                    best_match_name = "Unknown"
                    best_distance = float("inf")
                    
                    # --- TỐI ƯU THUẬT TOÁN SO KHỚP ---
                    # Thay vì dùng vòng lặp for (chậm với DB lớn), ta dùng Numpy Vectorization
                    # Trừ trực tiếp 1 vector emb với ma trận N vector db_embeddings
                    if len(db_embeddings) > 0:
                        distances = np.linalg.norm(db_embeddings - emb, axis=1)
                        min_idx = np.argmin(distances)
                        min_dist = distances[min_idx]
                        
                        if min_dist < THRESHOLD:
                            best_match_name = names[min_idx]
                            best_distance = min_dist
                                
                    color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = f"{best_match_name} ({best_distance:.2f})" if best_match_name != "Unknown" else "Unknown"
                    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("He Thong Kiem Soat Ra Vao (FaceNet)", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('r'):
            names, db_embeddings = load_registered_faces()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
