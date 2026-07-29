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
                             |  3.3V Power  (1)  (2)  5V Power [Đấu Ga MQ-2 VCC - Dây Đỏ]
                             |  GPIO 2      (3)  (4)  5V Power [Đấu Quạt VCC - Dây Đỏ]
                             |  GPIO 3      (5)  (6)  GND (Mát) [Đấu Quạt GND - Dây Đen]
                             |  GPIO 4      (7)  (8)  GPIO 14
[Ga MQ-2 GND - Dây Đen] <----|  GND (Mát)   (9)  (10) GPIO 15
                             |  GPIO 17    (11)  (12) GPIO 18  [Đấu Ga MQ-2 DO - Dây Vàng]
                             |  GPIO 27    (13)  (14) GND (Mát) [Đấu Còi Âm (-) - Dây Đen]
                             |  GPIO 22    (15)  (16) GPIO 23  (Trống) [Đấu LED Anode - Dây Xanh]
                             |  3.3V       (17)  (18) GPIO 24  [Đấu Còi Dương (+) - Dây Cam]
                            |  GPIO 10    (19)  (20) GND (Mát) [Đấu LED GND - Qua Điện trở]
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

## 3. Bảng tra cứu đấu nối thiết bị theo từng linh kiện (Grouped by Component)

Để việc lắp ráp được dễ dàng nhất, bạn hãy cầm từng linh kiện trên tay và thực hiện đấu nối theo sơ đồ phân nhóm dưới đây:

| STT | Thiết Bị Ngoại Vi | Chân Trên Thiết Bị | Chân Vật Lý Trên Pi 4 | Tên Chân Trên Pi (GPIO) | Màu Dây Khuyên Dùng | Cách Đấu Nối & Ghi Chú |
| :---: | :--- | :---: | :---: | :--- | :---: | :--- |
| **1** | **Cảm biến khí Ga MQ-2** | **VCC** | **Pin 2** | 5V Power | **Màu Đỏ** | Nối vào chân nguồn dương 5V của cảm biến. |
| | | **GND** | **Pin 9** | Ground (GND) | **Màu Đen / Nâu** | Nối vào chân đất của cảm biến. |
| | | **DO** | **Pin 12** | GPIO 18 | **Màu Vàng / Xanh** | Truyền tín hiệu số cảnh báo khí ga. |
| **2** | **Còi báo động vật lý** | **(+) Chân Dương** | **Pin 18** | GPIO 24 | **Màu Cam** | Nối vào chân dài (hoặc phía có dấu cộng +) của còi TMBI12A05. |
| | (Còi 2 chân TMBI12A05) | **(-) Chân Âm** | **Pin 14** | Ground (GND) | **Màu Đen** | Nối vào chân ngắn (cực âm) của còi. |
| **3** | **Đèn LED thông minh** | **Anode (+)** | **Pin 15** | GPIO 22 | **Màu Xanh lá** | Chân dài (+) cắm vào bảng cắm (Breadboard), nối dây về Pin 15. |
| | (Mô phỏng bật đèn tự động) | **Cathode (-)** | **Pin 20** | Ground (GND) | **Màu Đen** | Chân ngắn (-) cắm trên Breadboard, nối nối tiếp qua điện trở 220Ω rồi về Pin 20. |
| **4** | **Quạt tản nhiệt vỏ case** | **VCC** | **Pin 4** | 5V Power | **Màu Đỏ** (Dây sẵn) | Nối dây Đỏ của quạt để chạy tản nhiệt CPU. |
| | (Cooling Fan) | **GND** | **Pin 6** | Ground (GND) | **Màu Đen** (Dây sẵn) | Nối dây Đen của quạt để khép kín mạch. |

> [!TIP]
> **Ưu điểm của còi 2 chân TMBI12A05:**
> Do đây là loại còi Active Buzzer 2 chân, bạn có thể cấp nguồn và điều khiển trực tiếp từ chân GPIO 24 (Pin 18) và nối đất về Pin 14 mà không cần đấu chung nguồn 5V (Pin 2) qua breadboard, giúp giảm thiểu tối đa số lượng dây nối và đơn giản hóa mạch cắm.

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
* **Dây nguồn (VCC - Màu Đỏ)**: Nối chân VCC của cảm biến vào **Chân vật lý số 2** (chân 5V Power ở góc trên bên phải bo mạch).
* **Dây đất (GND - Màu Đen hoặc Màu Nâu)**: Nối chân GND của cảm biến vào **Chân vật lý số 9** (chân Ground).
* **Dây tín hiệu số (DO - Màu Vàng hoặc Màu Xanh lá)**: Nối chân DO (Digital Output) của cảm biến vào **Chân vật lý số 12 (GPIO 18)**.
* *Căn chỉnh cảm biến:* Trên module MQ-2 có một biến trở màu xanh dương. Sau khi hệ thống khởi động, dùng tuốc nơ vít nhỏ xoay biến trở để chỉnh độ nhạy: xoay sao cho đèn LED báo động trên cảm biến tắt trong không khí bình thường và lập tức sáng lên khi xịt nhẹ một ít khí ga (bật lửa gas).

### Bước 6: Đấu nối Còi báo động vật lý (Active Buzzer 2 chân TMBI12A05)
Chuẩn bị còi báo động Active Buzzer 5V loại 2 chân (ví dụ: mã TMBI12A05) và kết nối các chân cắm trực tiếp như sau:
* **Chân Dương (+ - chân dài hơn hoặc phía có đánh dấu + trên thân còi - Màu Cam)**: Cắm vào **Chân vật lý số 18 (GPIO 24)**.
* **Chân Âm (- - chân ngắn hơn - Màu Đen)**: Cắm vào **Chân vật lý số 14** (chân Ground).
* *Cơ chế hoạt động:* GPIO 24 sẽ trực tiếp xuất mức điện áp HIGH/LOW theo các chu kỳ xung nhịp để hú còi cảnh báo: Báo cháy (nháy cực nhanh 0.1s), Rò rỉ khí ga (nháy vừa 0.3s), Xâm nhập vùng cấm (nháy chậm 0.8s). Do còi được nuôi nguồn trực tiếp từ chân GPIO 24 nên không cần sử dụng thêm dây nguồn 5V ngoài.

### Bước 7: Kết nối Đèn LED chiếu sáng thông minh qua Bảng cắm (Breadboard) và Điện trở
Để mô phỏng hệ thống bật đèn tự động khi phát hiện chuyển động hoặc khi trời tối (hoặc bật/tắt thủ công qua Telegram/Web), bạn sử dụng **Bảng cắm testboard (Breadboard mini)** để đấu nối tiếp Đèn LED siêu sáng với Điện trở bảo vệ (220Ω - 330Ω) như sau:
1. **Cắm Đèn LED lên bảng cắm (Breadboard):** 
   * Cắm chân dài (Cực dương Anode +) và chân ngắn (Cực âm Cathode -) của LED vào hai hàng lỗ khác nhau trên Breadboard (ví dụ: hàng 10 và hàng 11).
2. **Nối dây tín hiệu điều khiển (Dây màu Xanh lá):**
   * Cắm một đầu dây jumper (Đực - Cái) vào cùng một hàng lỗ chứa chân dài (Anode +) của LED trên Breadboard.
   * Đầu dây Cái còn lại cắm vào **Chân vật lý số 15 (GPIO 22)** trên bo mạch Raspberry Pi 4.
3. **Mắc nối tiếp Điện trở bảo vệ:**
   * Cắm một chân của Điện trở (220Ω hoặc 330Ω) vào hàng lỗ chứa chân ngắn (Cathode -) của LED trên Breadboard.
   * Chân còn lại của Điện trở cắm sang một hàng lỗ trống khác trên Breadboard (ví dụ: hàng 12).
4. **Nối dây đất (Dây màu Đen):**
   * Cắm một đầu dây jumper (Đực - Cái) vào hàng lỗ chứa chân thứ hai của Điện trở trên Breadboard.
   * Đầu dây Cái còn lại cắm vào **Chân vật lý số 20 (GND)** trên Raspberry Pi 4.
* *Ưu điểm:* Việc sử dụng bảng cắm (Breadboard) giúp cố định chắc chắn chân đèn LED và điện trở, tránh các chân tiếp xúc chạm trực tiếp vào nhau gây đoản mạch làm hỏng cổng GPIO của Pi.

### Bước 8: Kết nối màn hình hiển thị trực quan (Tùy chọn)
* Nếu bạn cần cấu hình giao diện màn hình trực tiếp trên Pi, hãy cắm cáp chuyển đổi **Micro-HDMI** vào cổng HDMI sát cạnh cổng USB-C của Pi.
* Đầu cáp HDMI còn lại cắm vào cổng HDMI của màn hình máy tính hoặc TV.

### Bước 9: Cấp nguồn điện khởi động hệ thống (Thực hiện cuối cùng)
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
