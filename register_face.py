import cv2
import requests
import numpy as np

API_URL = "http://localhost:8000/register"

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Không thể mở webcam!")
        return

    print("--- ĐĂNG KÝ KHUÔN MẶT ---")
    print("1. Nhìn thẳng vào camera.")
    print("2. Nhấn phím 's' để chụp ảnh và đăng ký.")
    print("3. Nhấn phím 'q' để thoát.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Vẽ khung hướng dẫn
        h, w = frame.shape[:2]
        center_x, center_y = int(w/2), int(h/2)
        box_size = 200
        x1 = center_x - box_size // 2
        y1 = center_y - box_size // 2
        x2 = center_x + box_size // 2
        y2 = center_y + box_size // 2
        
        display_frame = frame.copy()
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(display_frame, "Dua mat vao khung va nhan 's'", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Dang ky khuon mat", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Hỏi tên
            name = input("\nNhập tên của bạn: ").strip()
            if not name:
                print("Tên không được để trống!")
                continue
            
            print(f"Đang gửi ảnh của {name} lên máy chủ...")
            
            # Chuyển đổi frame (ảnh gốc, không có khung xanh) sang jpeg bytes
            success, encoded_image = cv2.imencode('.jpg', frame)
            if not success:
                print("Lỗi mã hóa hình ảnh!")
                continue
            
            files = {'file': ('face.jpg', encoded_image.tobytes(), 'image/jpeg')}
            data = {'name': name}
            
            try:
                response = requests.post(API_URL, files=files, data=data)
                if response.status_code == 200:
                    print("=> Thành công:", response.json())
                else:
                    print("=> Thất bại:", response.text)
            except requests.exceptions.ConnectionError:
                print("=> LỖI: Không thể kết nối đến máy chủ. Hãy chắc chắn bạn đã chạy 'python face_api.py'")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
