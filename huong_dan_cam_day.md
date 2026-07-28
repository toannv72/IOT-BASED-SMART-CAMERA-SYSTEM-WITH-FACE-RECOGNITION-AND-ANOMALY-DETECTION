# HƯỚNG DẪN CẮM DÂY VÀ KẾT NỐI PHẦN CỨNG RASPBERRY PI 4

Tài liệu này hướng dẫn chi tiết toàn bộ quá trình lắp đặt phần cứng, đấu nối cảm biến, còi báo động và các kết nối ngoại vi trên bo mạch **Raspberry Pi 4 Model B (8GB/4GB RAM)** để tạo thành một nút biên (Edge Node) AI hoàn chỉnh từ đầu đến cuối.

> [!IMPORTANT]
> **QUY TẮC AN TOÀN ĐIỆN VẬT LÝ:**
> Hãy luôn ngắt nguồn điện (rút nguồn USB-C) trước khi thực hiện cắm hoặc rút bất kỳ dây cáp, chân GPIO hay cảm biến nào. Việc đấu nối dây khi bo mạch đang có điện có thể gây chập mạch, làm hỏng các chân GPIO hoặc gây cháy chip CPU của Raspberry Pi. Chỉ cắm nguồn cấp điện ở bước cuối cùng sau khi đã kiểm tra kỹ toàn bộ các mối nối.

---

## 1. Sơ đồ kết nối phần cứng tổng quan (ASCII Diagram)

```text
               +----------------------------------------------------+
               |                RASPBERRY PI 4 MODEL B              |
               |                                                    |
  [Quạt 5V] --->| [GPIO Pins]  (Cắm chân Đỏ -> chân 4, Đen -> chân 6)
 [Cảm biến Ga]->|              (VCC -> chân 2 (5V), GND -> chân 9, DO -> chân 12 (GPIO 18))
 [Còi báo động]->|             (VCC -> chân 2 (5V) chia sẻ, GND -> chân 14, IN -> chân 18 (GPIO 24))
                |                                                    |
 [Nguồn USB-C] | [USB-C Port] (Cấp nguồn 5V-3A - CẮM SAU CÙNG)     |
   (Cắm điện)  |                                                    |
               | [Micro-HDMI] (Cổng HDMI 1 - Xuất màn hình tùy chọn)|
               |                                                    |
               | [USB 2.0 - Đen]                                    |
               | [USB 2.0 - Đen]                                    |
               |                                                    |
 [USB Webcam] -| [USB 3.0 - Xanh] (Cắm Webcam ở đây để có tốc độ cao)|
               | [USB 3.0 - Xanh]                                   |
               |                                                    |
  [Cáp Mạng] --| [Ethernet RJ45] (Kết nối mạng LAN cùng với Laptop)  |
               +----------------------------------------------------+
                        |
                        | (Cáp Ethernet RJ45 hoặc kết nối qua Wi-Fi)
                        v
               +----------------------------------------------------+
               |                  ROUTER WI-FI / SWITCH             |
               |       (Cấp phát địa chỉ IP cho Pi 4 và Laptop)     |
               +----------------------------------------------------+
                        ^
                        | (Kết nối cùng mạng LAN của Router)
                        v
               +----------------------------------------------------+
               |                 LAPTOP CÁ NHÂN (CLIENT)            |
               |       (Dùng để điều khiển SSH & Xem Web Dashboard)  |
               +----------------------------------------------------+
```

---

## Sơ đồ đấu nối trực quan (Visual Wiring Diagram)

![Sơ đồ kết nối phần cứng vật lý](static/raspberry_pi_wiring_diagram.png)

---

## 2. Sơ đồ hàng chân cắm 40-Pin GPIO chi tiết (Top View)

Dưới đây là sơ đồ bố trí hàng chân cắm **40-Pin GPIO** trên Raspberry Pi 4 để bạn dễ đối chiếu số thứ tự chân vật lý (1-40):

```text
                                MẶT TRÊN BO MẠCH (TOP VIEW)
                             Hàng Lẻ (Trong)    Hàng Chẵn (Ngoài)
                            +------------------------------------+
                            |  3.3V Power  (1)  (2)  5V Power [Đấu Ga/Còi VCC]
                            |  GPIO 2      (3)  (4)  5V Power [Đấu Quạt VCC]
  [Cực âm Quạt GND] <-------|  GND (Mát)   (5)  (6)  GND (Mát) [Đấu dây Đen Quạt]
                            |  GPIO 4      (7)  (8)  GPIO 14
   [Ga MQ-2 GND] <----------|  GND (Mát)   (9)  (10) GPIO 15
                            |  GPIO 17    (11)  (12) GPIO 18  [Đấu Ga MQ-2 DO]
                            |  GPIO 27    (13)  (14) GND (Mát) [Đấu Còi GND]
                            |  GPIO 22    (15)  (16) GPIO 23  (Trống)
                            |  3.3V       (17)  (18) GPIO 24  [Đấu Còi báo IN]
                            |  GPIO 10    (19)  (20) GND (Mát)
                            |  GPIO 9     (21)  (22) GPIO 25
                            |  GPIO 11    (23)  (24) GPIO 8
                            |  GND (Mát)  (25)  (26) GPIO 7
                            |  GPIO 0     (27)  (28) GPIO 1
                            |  GPIO 5     (29)  (30) GND (Mát)
                            |  GPIO 6     (31)  (32) GPIO 12
                            |  GPIO 13    (33)  (34) GND (Mát)
                            |  GPIO 19    (35)  (36) GPIO 16
                            |  GPIO 26    (37)  (38) GPIO 20
                            |  GND (Mát)  (39)  (40) GPIO 21
                            +------------------------------------+
```

---

## 3. Bảng tra cứu đấu nối thiết bị theo chân vật lý

| Số Chân Vật Lý | Tên Chân (GPIO) | Thiết Bị Ngoại Vi | Đầu Dây Thiết Bị | Ý Nghĩa & Cách Đấu Nối |
| :---: | :--- | :--- | :---: | :--- |
| **2** | 5V Power | Cảm biến Ga MQ-2 & Còi báo động | **VCC** / **(+)** | **Đấu chung**: Nối nguồn dương (5V) của cả cảm biến Ga và Còi hú vào chân này. |
| **4** | 5V Power | Quạt tản nhiệt vỏ case | **VCC** / **(+)** | Nối dây Đỏ (Cực dương) của Quạt tản nhiệt vào chân này. |
| **6** | Ground (GND) | Quạt tản nhiệt vỏ case | **GND** / **(-)** | Nối dây Đen (Cực âm) của Quạt tản nhiệt vào chân này. |
| **9** | Ground (GND) | Cảm biến khí Ga MQ-2 | **GND** | Nối dây đất (GND) của cảm biến khí ga vào chân này. |
| **12** | GPIO 18 | Cảm biến khí Ga MQ-2 | **DO** (Digital Output) | Truyền tín hiệu số (High/Low) về Pi khi nồng độ ga vượt ngưỡng. |
| **14** | Ground (GND) | Còi báo động (Active Buzzer) | **GND** | Nối dây âm/đất (GND) của còi báo động vào chân này. |
| **18** | GPIO 24 | Còi báo động (Active Buzzer) | **IN** / **I/O** | Xuất mức điện áp điều khiển còi hú theo các chu kỳ báo động khác nhau. |

> [!TIP]
> **Giải pháp chia sẻ cổng nguồn (VCC/GND):**
> Do Raspberry Pi chỉ có một số chân nguồn 5V và GND vật lý, bạn nên đấu chụm các đầu dây cấp nguồn lại với nhau bằng testboard chia nguồn (Mini Breadboard) hoặc cầu đấu nối để đảm bảo mối nối chắc chắn, an toàn và thẩm mỹ.

---

## 4. Quy trình lắp đặt và cắm dây chi tiết (Từng bước từ đầu đến cuối)

Hãy tuân thủ thứ tự các bước dưới đây để quá trình lắp ráp diễn ra an toàn và chính xác nhất:

### Bước 1: Lắp thẻ nhớ MicroSD chứa hệ điều hành
* Chuẩn bị thẻ nhớ MicroSD (từ 32GB trở lên) đã được flash sẵn hệ điều hành **Raspberry Pi OS (64-bit)**.
* Lật mặt dưới của bo mạch Raspberry Pi 4, tìm khe cắm thẻ nhớ MicroSD ở sát cạnh cổng USB-C.
* Cắm thẻ nhớ vào đúng khớp (mặt có các chân đồng màu vàng hướng về phía bảng mạch bo mạch Pi). Đẩy nhẹ thẻ vào cho tới khi khớp chắc chắn.

### Bước 2: Gắn bo mạch vào Case và lắp quạt tản nhiệt
* Dán các miếng dẫn nhiệt màu xanh (Thermal Pads) đi kèm vỏ case lên các bề mặt chip: CPU Broadcom (ở giữa), chip RAM (bên cạnh CPU) và chip quản lý nguồn.
* Đặt bo mạch Raspberry Pi 4 vào bên trong case nhựa hoặc nhôm.
* Lắp quạt tản nhiệt 5V lên nắp case hoặc gắn trực tiếp trên CPU.
* Đấu nối 2 dây nguồn của quạt vào hàng chân GPIO:
  * **Dây Đỏ (5V)**: Cắm vào **Chân vật lý số 4**.
  * **Dây Đen (GND)**: Cắm vào **Chân vật lý số 6**.

### Bước 3: Cắm thiết bị thu nhận hình ảnh (USB Webcam)
* Cắm đầu dây USB của Webcam vào một trong hai cổng **USB 3.0 (Cổng màu xanh dương)** trên bo mạch Raspberry Pi 4.
* *Lưu ý:* Tránh cắm vào các cổng USB 2.0 màu đen vì cổng này có băng thông dữ liệu hẹp, có thể gây giật lag hoặc giảm tốc độ xử lý khung hình của luồng camera đưa vào mô hình AI.

### Bước 4: Kết nối cáp mạng LAN nội bộ
* Cắm một đầu cáp mạng Ethernet RJ45 vào cổng mạng **LAN** của Raspberry Pi 4.
* Đầu cáp còn lại cắm vào cổng LAN trống trên **Router Wi-Fi** hoặc **Switch** trong phòng.
* Đảm bảo Laptop cá nhân của bạn cũng kết nối cùng một mạng Wi-Fi hoặc mạng dây từ Router này để thiết lập mạng LAN nội bộ phục vụ kết nối VNC/SSH và Web Dashboard.

### Bước 5: Kết nối cảm biến khí Ga MQ-2
Chuẩn bị cảm biến khí Ga MQ-2 và 3 sợi dây jumper nối Cái - Cái:
* **Dây nguồn (VCC)**: Nối chân VCC của cảm biến vào **Chân vật lý số 2** (chân 5V Power ở góc trên bên phải bo mạch).
* **Dây đất (GND)**: Nối chân GND của cảm biến vào **Chân vật lý số 9** (chân Ground).
* **Dây tín hiệu số (DO)**: Nối chân DO (Digital Output) của cảm biến vào **Chân vật lý số 12 (GPIO 18)**.
* *Căn chỉnh cảm biến:* Trên module MQ-2 có một biến trở màu xanh dương. Sau khi hệ thống khởi động, dùng tuốc nơ vít nhỏ xoay biến trở để chỉnh độ nhạy: xoay sao cho đèn LED báo động trên cảm biến tắt trong không khí bình thường và lập tức sáng lên khi xịt nhẹ một ít khí ga (bật lửa gas).

### Bước 6: Đấu nối Còi báo động vật lý (Active Buzzer 5V)
Chuẩn bị còi báo động Active Buzzer 5V và kết nối các chân cắm:
* **Dây nguồn (VCC/+)**: Nối vào **Chân vật lý số 2** (đấu song song/chia sẻ với chân nguồn của cảm biến Ga MQ-2 bằng testboard mini).
* **Dây đất (GND/-)**: Nối vào **Chân vật lý số 14** (chân Ground).
* **Dây tín hiệu điều khiển (IN)**: Nối chân tín hiệu còi vào **Chân vật lý số 18 (GPIO 24)**.
* *Cơ chế hoạt động:* GPIO 24 sẽ xuất nhịp xung HIGH/LOW liên tục để hú còi tùy theo mức độ nguy hại: Báo cháy (nháy cực nhanh 0.1s), Rò rỉ khí ga (nháy vừa 0.3s), Xâm nhập vùng cấm (nháy chậm 0.8s).

### Bước 7: Kết nối màn hình hiển thị trực quan (Tùy chọn)
* Nếu bạn cần cấu hình giao diện màn hình trực tiếp trên Pi, hãy cắm cáp chuyển đổi **Micro-HDMI** vào cổng HDMI sát cạnh cổng USB-C của Pi.
* Đầu cáp HDMI còn lại cắm vào cổng HDMI của màn hình máy tính hoặc TV.

### Bước 8: Cấp nguồn điện khởi động hệ thống (Thực hiện cuối cùng)
* Sau khi đã rà soát kỹ tất cả các vị trí chân cắm, cắm đầu cáp nguồn **USB-C** (Nguồn dòng 5V-3A ổn định) vào cổng USB-C trên Pi.
* Cắm củ nguồn vào ổ cắm điện. Bo mạch sẽ tự khởi động. Đèn LED đỏ (Power) trên bo mạch sáng liên tục và đèn LED xanh lá (ACT) nhấp nháy báo hiệu đang đọc hệ điều hành từ thẻ nhớ.

---

## 5. Hướng dẫn kiểm tra và vận hành hệ thống

1. **Kiểm tra IP:** Sử dụng phần mềm quét IP (như *Advanced IP Scanner* trên Windows) hoặc truy cập trang quản trị Router để tìm địa chỉ IP cục bộ của Pi (Ví dụ: `192.168.1.15`).
2. **Khởi động mã nguồn:** Mở Terminal (qua SSH hoặc trực tiếp trên màn hình Pi), di chuyển đến thư mục dự án và chạy chương trình:
   ```bash
   python main.py
   ```
3. **Truy cập hệ thống:** Trên trình duyệt web của Laptop, truy cập vào địa chỉ IP của Pi theo cổng 8000:
   `http://192.168.1.15:8000`
4. **Chạy thử cảm biến:** Thử xịt nhẹ khí ga vào đầu cảm biến MQ-2, quan sát xem đèn báo trên Web lập tức chuyển đỏ, còi hú vật lý nhấp nháy chu kỳ 0.3 giây và Telegram gửi tin nhắn cảnh báo rò rỉ ga kèm ảnh chụp camera về điện thoại hay không.
