import cv2
import requests
import torch
import numpy as np
import argparse
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image

API_URL_EMBEDDINGS = "http://localhost:8000/embeddings"
THRESHOLD = 0.8 # Ngưỡng nhận diện (càng nhỏ càng khắt khe)

def load_registered_faces():
    try:
        response = requests.get(API_URL_EMBEDDINGS)
        if response.status_code == 200:
            data = response.json()
            for person in data:
                person["embedding"] = np.array(person["embedding"])
            return data
        return []
    except Exception as e:
        print("Lỗi: Không thể kết nối đến face_api.py. Vui lòng đảm bảo API đang chạy.")
        return []

def recognize_faces_in_image(image_path):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    mtcnn = MTCNN(keep_all=True, device=device)
    resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    registered_faces = load_registered_faces()
    if not registered_faces:
        print("Cơ sở dữ liệu trống. Vui lòng đăng ký khuôn mặt trước!")
        return

    # Đọc ảnh
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Lỗi: Không thể đọc ảnh từ {image_path}")
        return

    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    # Phát hiện khuôn mặt
    boxes, _ = mtcnn.detect(img_pil)
    
    if boxes is not None:
        faces = mtcnn(img_pil)
        if faces is not None:
            embeddings = resnet(faces.to(device)).detach().cpu().numpy()
            
            for i, (box, emb) in enumerate(zip(boxes, embeddings)):
                x1, y1, x2, y2 = [int(b) for b in box]
                
                best_match_name = "Unknown"
                best_distance = float("inf")
                
                # So khớp
                for person in registered_faces:
                    dist = np.linalg.norm(emb - person["embedding"])
                    if dist < best_distance:
                        best_distance = dist
                        if dist < THRESHOLD:
                            best_match_name = person["name"]
                            
                color = (0, 255, 0) if best_match_name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                text = f"{best_match_name} ({best_distance:.2f})"
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                print(f"Phat hien: {best_match_name} với khoảng cách {best_distance:.2f}")

    # Hiển thị ảnh
    cv2.imshow("Nhan dien tren anh", frame)
    print("Nhấn phím bất kỳ trên cửa sổ ảnh để thoát...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    # Nếu người dùng truyền vào đường dẫn file, ví dụ: python recognize_image.py anh_cua_toi.jpg
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        # File mặc định để test nếu không truyền tham số
        img_path = "test.jpg"
        print(f"Bạn chưa truyền đường dẫn ảnh. Đang thử nhận diện file mặc định: {img_path}")
        
    recognize_faces_in_image(img_path)
