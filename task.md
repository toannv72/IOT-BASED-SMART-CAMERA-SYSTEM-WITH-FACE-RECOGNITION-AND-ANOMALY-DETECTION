# Danh sách công việc & Kiểm thử xác nhận (Task Checklist & Verification)

## 1. Tải dữ liệu từ Kaggle
- [x] Tải tập dữ liệu 9.37 GB từ Kaggle về ổ D (`d:\CODE\yolo\kaggle_cache`)
  * *Xác nhận:* Đã hoàn thành tải về thành công.

## 2. Giải nén dữ liệu
- [x] Giải nén tập dữ liệu ImViA sang thư mục cache trên ổ D
  * *Xác nhận:* Đã giải nén xong các thư mục môi trường `Home`, `Office`, `Coffee_room`, `Lecture_room` chứa đầy đủ video và annotation.

## 3. Tiền xử lý & Trích xuất ảnh (YOLO Format)
- [x] Chạy `python preprocess_dataset.py` để lọc ảnh và sinh nhãn YOLOv8
  * *Xác nhận:* Đã hoàn thành lọc ảnh và trích xuất nhãn YOLO thành công (Train: 35,041 ảnh, Val: 6,989 ảnh). Đã sinh file cấu hình `data.yaml`.

## 4. Huấn luyện mô hình YOLOv8n-fall
- [x] Chạy `python train_yolo.py` để huấn luyện mô hình trên GPU CUDA (Hoàn thành)
  * *Xác nhận 1:* Biểu đồ mất mát (loss) giảm dần và độ chính xác (mAP50) tăng dần, được lưu trong thư mục `runs/detect/runs/train_fall/yolov8n_fall/`.
  * *Xác nhận 2:* Tệp trọng số tốt nhất `yolov8n_fall_best.pt` được tạo ra ở thư mục gốc của dự án.

## 5. Tích hợp & Kiểm thử trên Web Dashboard
- [x] Khởi chạy lại Web Dashboard (`web_app.py`) tích hợp mô hình mới huấn luyện (Đã hoàn thành)
  * *Xác nhận 1:* Camera 5 đã tải thành công mô hình `yolov8n_fall_best.pt` tự train (Nhãn `Normal` màu xanh lá, Nhãn `FALL` màu đỏ).
  * *Xác nhận 2:* Khi phát hiện ngã (nhãn `FALL`), Web Dashboard ghi nhận sự kiện danger vào Nhật ký sự kiện trực tuyến, chớp chuông đỏ và gửi ảnh cảnh báo qua Telegram.
  * *Xác nhận 3:* Đã tạo tập lệnh kiểm thử video độc lập [test_fall_video.py](file:///d:/CODE/yolo/test_fall_video.py) và tích hợp vào Menu chính [chay_he_thong.bat](file:///d:/CODE/yolo/chay_he_thong.bat) (Lựa chọn 9) để chạy thử nghiệm trực tiếp trên video.
