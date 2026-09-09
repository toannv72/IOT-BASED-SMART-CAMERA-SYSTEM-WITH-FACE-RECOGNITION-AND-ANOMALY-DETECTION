# 📸 DANH SÁCH TOÀN BỘ CÁC ẢNH CẦN CHỤP THỰC TẾ ĐỂ CHÈN VÀO BÀI BẢO VỆ ĐỒ ÁN

> **Đề tài:** Hệ thống Smart Camera giám sát đa nguy cơ biên (Edge AI) trên Raspberry Pi 4 Model B (4GB RAM)  
> **Tệp trình chiếu PowerPoint:** `thuyet_trinh_do_an.pptx` (21 slides chuẩn Widescreen 16:9)

Tài liệu này tổng hợp chi tiết **toàn bộ các ảnh chụp thực tế bên ngoài** mà bạn cần chụp để chèn vào các khung placeholder `📷 [ẢNH CẦN CHỤP THỰC TẾ]` đã được thiết kế sẵn trên từng slide tương ứng.

---

## I. BẢNG TỔNG HỢP CÁC ẢNH CẦN CHỤP THEO TỪNG SLIDE

| STT | Vị Trí Slide | Tên Slide / Nội Dung | Số Lượng Ảnh | Mô Tả Ảnh Cần Chụp | Hướng Dẫn Trạng Thái & Góc Chụp |
| :---: | :---: | :--- | :---: | :--- | :--- |
| **1** | **Slide 6** | Pipeline thị giác máy tính đa nguy cơ | 1 ảnh | Bàn làm việc/thí nghiệm thực tế với Raspberry Pi 4 | Chụp từ trên xuống góc 45°: Thấy rõ bo mạch Pi 4, quạt tản nhiệt đang quay, 2 webcam USB cắm cổng USB 3.0 và màn hình laptop đang stream video. |
| **2** | **Slide 7** | Thuật toán nhận diện khẩu trang 1 ảnh mẫu | 1 ảnh (Screenshot) | Màn hình Web Dashboard nhận diện người đeo khẩu trang | Chụp màn hình Web Dashboard: Bạn đang đeo khẩu trang trước webcam, trên video xuất hiện **bounding box màu xanh** có tên bạn và khoảng cách L2 (ví dụ: `Toan - 0.68`). |
| **3** | **Slide 8** | Mô hình YOLOv8 & Hàng rào ảo ROI | 1 ảnh (Screenshot) | Giao diện vẽ đa giác vùng cấm ROI trên Web Dashboard | Chụp màn hình Web Dashboard phần cài đặt camera: Thấy rõ khung video camera và các nét vẽ đa giác ROI màu đỏ/xanh viền quanh khu vực cửa bảo vệ. |
| **4** | **Slide 10** | Sơ đồ kết nối chân cắm GPIO ngoại vi | 1 ảnh | Cận cảnh hàng chân GPIO trên Raspberry Pi 4 | Chụp macro cận cảnh hàng 40 chân GPIO của Pi 4 với các dây jumper màu cắm vào chân 12 (GPIO 18), chân 16 (GPIO 23), chân 18 (GPIO 24), 5V và GND. |
| **5** | **Slide 11** | Sơ đồ mạch điện tử & Thiết bị hoàn chỉnh | 1 ảnh | Toàn bộ mô hình phần cứng hoàn chỉnh đặt trên bàn | Chụp góc rộng toàn cảnh: Bo mạch Pi 4 cắm nguồn, 2 webcam USB, module rơ-le, khóa cửa solenoid, cảm biến gas MQ-2, còi buzzer và adapter nguồn 12V. |
| **6** | **Slide 12** | Nền tảng điều khiển Web Dashboard (SSE) | 1 ảnh (Screenshot) | Toàn cảnh giao diện Web Dashboard đang hoạt động | Chụp toàn màn hình trình duyệt: Thấy rõ 2 khung video stream từ 2 camera, thanh trạng thái cảm biến gas, nút kích mở khóa cửa và bảng nhật ký log sự kiện. |
| **7** | **Slide 13** | Telegram Bot 2 chiều & Khôi phục mất điện | 1 ảnh (Screenshot) | Màn hình điện thoại chat với Smart Camera Telegram Bot | Chụp màn hình điện thoại mở app Telegram: Thấy tin nhắn báo động kèm ảnh hiện trường từ bot và các nút bấm Inline: `[🔕 Tắt báo động]`, `[🔓 Mở khóa cửa]`. |
| **8** | **Slide 14** | Thực nghiệm 1: Nhận diện khuôn mặt | 2 ảnh (Screenshots) | (1) Nhận diện khi KHÔNG đeo khẩu trang.<br>(2) Nhận diện khi ĐEO KHẨU TRANG y tế. | • Ảnh 1: Bạn đứng trước camera mặt mộc ➔ Bounding box xanh hiện tên bạn.<br>• Ảnh 2: Chính bạn đeo khẩu trang y tế đứng trước camera ➔ Vẫn nhận diện đúng tên bạn! |
| **9** | **Slide 15** | Thực nghiệm 2: Phát hiện Té ngã & ROI | 2 ảnh | (1) Người nằm ngã trên sàn nhà.<br>(2) Người bước vào vùng cấm ROI. | • Ảnh 1: Mô phỏng người ngã nằm trên sàn, camera nhận diện nhãn `fall` màu đỏ/vàng.<br>• Ảnh 2: Người bước chân vào vùng đa giác ROI màu đỏ và hệ thống báo động `Intrusion`. |
| **10** | **Slide 16** | Thực nghiệm 3: Báo cháy & Cảm biến MQ-2 | 2 ảnh | (1) Ngọn lửa bật lửa trước camera.<br>(2) Bật lửa xì gas vào cảm biến MQ-2. | • Ảnh 1: Bật ngọn lửa/que diêm trước webcam ➔ Trên màn hình xuất hiện khung `fire`.<br>• Ảnh 2: Đưa đầu bật lửa xì gas vào đầu cảm biến MQ-2 ➔ Đèn đỏ DO sáng lên và còi buzzer hú. |
| **11** | **Slide 17** | Thực nghiệm 4: Khóa Solenoid 3s & Mất điện | 2 ảnh | (1) Chốt khóa Solenoid đang thụt vào mở cửa.<br>(2) Tin nhắn Telegram xác nhận mở cửa. | • Ảnh 1: Cận cảnh chốt khóa Solenoid đang thụt vào trong khi nhận lệnh mở cửa và đèn LED rơ-le sáng.<br>• Ảnh 2: Ảnh màn hình điện thoại nhận tin nhắn Telegram: *"Đã mở khóa cửa thành công (tự khóa lại sau 3s)"*. |

---

## II. HƯỚNG DẪN CÁCH CHỤP TỪNG BỘ ẢNH ĐẠT CHUẨN

### 1. Nhóm ảnh chụp thực tế Phần cứng & Thiết bị (Chụp bằng điện thoại)
* **Góc chụp:** Bật đèn sáng đầy đủ, lau sạch camera điện thoại. Đặt bo mạch và dây nối gọn gàng trên bàn màu sáng (bàn gỗ hoặc bàn trắng).
* **Ảnh Bo mạch Pi 4 & Ngoại vi (Slide 6, 10, 11):**
  * Cắm nguồn để đèn đỏ nguồn (PWR) và đèn xanh đọc thẻ nhớ (ACT) trên Pi 4 sáng.
  * Quạt tản nhiệt đang quay để chứng minh hệ thống đang chạy thật trên CPU nhúng.
  * Các dây cắm rơ-le, cảm biến gas MQ-2 và khóa Solenoid được căng ngay ngắn.
* **Ảnh Khóa Solenoid mở (Slide 17):**
  * Nhờ một người bấm nút mở cửa trên Web hoặc gửi `/unlock` trên Telegram.
  * Ngay trong 3 giây rơ-le đang hút, chụp cận cảnh thanh chốt sắt của khóa thụt sâu vào trong thân khóa và đèn đỏ trên rơ-le đang sáng.
* **Ảnh Test Khí Ga MQ-2 (Slide 16):**
  * Dùng bật lửa ga (nhấn nút xì ga nhưng không quẹt lửa), đưa đầu xì ga cách đầu cảm biến MQ-2 khoảng 1 - 2 cm.
  * Chụp ảnh khi đèn LED báo Digital Output (DO) trên bo cảm biến chuyển sang sáng đỏ.

### 2. Nhóm ảnh chụp màn hình máy tính (Web Dashboard)
* **Cách chụp sắc nét:** Bấm tổ hợp phím `Windows + Shift + S` trên Windows để chụp vùng màn hình sắc nét nhất (không chụp điện thoại vào màn hình vì sẽ bị sọc ma trận).
* **Ảnh Nhận diện khẩu trang (Slide 7, 14):**
  * Đứng trước webcam sao cho khuôn mặt nằm rõ trong khung hình.
  * Chụp 1 tấm mặt mộc: Khung xanh hiện tên bạn + khoảng cách L2 (ví dụ: `Toan - 0.42`).
  * Đeo khẩu trang y tế che kín mũi và cằm, chụp tấm thứ 2: Khung xanh vẫn hiện tên bạn + khoảng cách L2 (ví dụ: `Toan - 0.68`).
* **Ảnh Vẽ ROI (Slide 8):**
  * Vào mục cấu hình camera trên Web, dùng chuột chấm 4 góc đa giác viền đỏ bao quanh lối cửa ra vào.
  * Chụp lại màn hình khi các đường viền đa giác nét đứt màu đỏ đang hiển thị rõ trên luồng video.
* **Ảnh Báo cháy & Té ngã (Slide 15, 16):**
  * Quẹt que diêm hoặc bật lửa trước camera, chụp màn hình khi mô hình YOLOv8 đóng khung chữ nhật màu cam/đỏ có chữ `fire: 0.92`.
  * Nằm thử nghiệm giả lập tư thế ngã trên sàn, chụp màn hình khi mô hình đóng khung chữ nhật có nhãn `fall: 0.88`.

### 3. Nhóm ảnh chụp màn hình điện thoại (Telegram Bot)
* Mở đoạn chat với Bot Smart Camera trên ứng dụng Telegram của bạn.
* Chụp ảnh màn hình điện thoại (Screenshot) có:
  * Tin nhắn thông báo: *"🚨 PHÁT HIỆN NGUY CƠ: Có người lạ xâm nhập / Phát hiện đám cháy"* kèm ảnh chụp hiện trường gửi từ camera.
  * Các nút bấm tương tác Inline ở dưới: `[🔕 Tắt báo động]` | `[⏸ Tạm dừng 30s]` | `[🔓 Mở khóa cửa]`.
  * Tin nhắn xác nhận: *"✅ Đã kích hoạt mở khóa Solenoid trong 3 giây."*

---

## III. CÁCH CHÈN ẢNH VÀO FILE SLIDE `thuyet_trinh_do_an.pptx`

1. Mở file **`thuyet_trinh_do_an.pptx`** bằng Microsoft PowerPoint.
2. Di chuyển đến từng slide có khung viền màu vàng/cam ghi chú `📷 [ẢNH CẦN CHỤP THỰC TẾ]`.
3. Nhấp chọn khung ghi chú đó và bấm phím `Delete` để xóa khung hướng dẫn đi.
4. Bấm vào menu **Insert ➔ Pictures (Chèn ảnh)** trên thanh công cụ PowerPoint, chọn file ảnh bạn vừa chụp để chèn vào đúng vị trí đó.
5. Kéo thả kích thước ảnh cho vừa vặn với bố cục slide.
6. Bấm `Ctrl + S` để lưu lại.
