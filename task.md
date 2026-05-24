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

## 6. Cải tiến tương tác Đếm người đa kênh (Interactive Line Drawing & Roboflow Supervision Integration)
- [x] Cập nhật `multi_cam_counter.py` sử dụng thư viện chuyên dụng Roboflow Supervision (Đã hoàn thành)
  * *Xác nhận 1:* Tích hợp thành công thư viện chuyên dụng **Roboflow Supervision** (`sv.LineZone`, `sv.LineZoneAnnotator`, `sv.Position.BOTTOM_CENTER`).
  * *Xác nhận 2:* Người dùng có thể click chuột trái 2 lần trên cửa sổ camera để thiết lập vạch kẻ ra vào mới, tự động lưu vào `cameras_config.json`.
  * *Xác nhận 3:* Thuật toán vector định hướng và bộ nhớ vết (tracking history memory) của Supervision giúp loại bỏ hoàn toàn hiện tượng đếm lặp / đếm sai khi người đi lại gần vạch kẻ hoặc đứng im dao động.

## 7. Khắc phục lỗi đếm sai khi nhiều người đi qua vạch cùng lúc (Crowd Tracking & Split-Track Correction)
- [x] Tối ưu hóa bám vết và đồng bộ thuật toán đếm (Đã hoàn thành)
  * *Xác nhận 1:* Tạo tệp cấu hình [custom_bytetrack.yaml](file:///d:/CODE/yolo/custom_bytetrack.yaml) tối ưu bám vết đám đông (hạ threshold bám vết yếu xuống 0.05, tăng buffer lưu vết lên 90 frames).
  * *Xác nhận 2:* Đồng bộ hóa luồng Web Dashboard để nạp vạch đếm động từ `cameras_config.json` vẽ bởi GUI và tích hợp Supervision giúp đồng nhất kết quả hiển thị.
  * *Xác nhận 3:* Nâng cấp mô hình đếm người từ `yolov8n.pt` lên mô hình chính xác hơn `yolov8s.pt` (Small - 11.2M params) trong cả `multi_cam_counter.py` và `web_app.py` để phát hiện người che khuất tốt hơn.
  * *Xác nhận 4:* Triển khai thành công giải thuật bù đếm khi tách vết (Split-Track Heuristic) giúp tự động bù thêm đếm +1 khi 2 người đi đè lấp qua vạch rồi tách nhau ra sau đó.

## 8. Đếm vạch đôi song song (Double-Line Crossing State Machine)
- [x] Triển khai giải thuật đếm vạch đôi song song chiếu tọa độ và bám vết lịch sử mất dấu (Đã hoàn thành)
  * *Xác nhận 1:* Thay thế vạch đơn bằng 2 vạch song song (Vạch Ngoài và Vạch Trong, cách nhau 60px) tự động tính toán pháp tuyến của vạch vẽ.
  * *Xác nhận 2:* Sử dụng máy trạng thái chiếu tọa độ giúp loại bỏ triệt để dập dình nhảy vạch, chỉ tăng IN khi đi hoàn toàn từ Ngoài vào Trong, tăng OUT khi đi từ Trong ra Ngoài.
  * *Xác nhận 3:* Tích hợp bộ nhớ lịch sử mất dấu `lost_tracks` để thừa kế trạng thái di chuyển khi người bị đổi ID lúc đi qua vạch.
  * *Xác nhận 4:* Đồng bộ hóa giao diện vẽ 2 vạch và số đếm chính xác trên cả GUI (`multi_cam_counter.py`) và Web Dashboard (`web_app.py`).

## 9. Tối ưu hóa đếm vạch đôi & Khắc phục đứng hình cảnh báo xâm nhập
- [x] Chỉnh sửa `web_app.py` để gửi cảnh báo Telegram bất đồng bộ (Thread)
- [x] Nâng cấp mô hình đếm người của Web Dashboard lên `yolov8s.pt`
- [x] Tích hợp bộ đếm vạch đôi cải tiến (cooldown, dynamic distance) trong `web_app.py`
- [x] Đồng bộ bộ đếm cải tiến trong `multi_cam_counter.py`
- [x] Chạy thử nghiệm và xác nhận kết quả

## 10. Tái cấu trúc Modular, Đăng ký/Đăng nhập người dùng & Giám sát sức khỏe phần cứng
- [x] Thiết kế cấu trúc thư mục modular chuyên nghiệp dưới gói `app/`
- [x] Triển khai custom `HMACSessionMiddleware` thay thế `SessionMiddleware` của Starlette tránh phụ thuộc thư viện ngoài `itsdangerous`
- [x] Tạo màn hình Đăng ký/Đăng nhập dạng Glassmorphism bảo mật các luồng video và API settings
- [x] Tạo widget giám sát sức khỏe CPU, RAM, GPU, VRAM và FPS thực tế của từng camera giám sát
- [x] SQLite-based historical alert event log lưu lịch sử cảnh báo cùng đường dẫn ảnh sự kiện chụp được
- [x] Cấu hình động thông số AI trực tiếp trên giao diện Dashboard không cần restart
- [x] Loại bỏ file monolithic `web_app.py` và cập nhật các tệp tin batch khởi chạy `chay_he_thong.bat` và hướng dẫn vận hành
- [x] Chạy thử nghiệm và xác nhận toàn bộ hệ thống hoạt động chính xác
