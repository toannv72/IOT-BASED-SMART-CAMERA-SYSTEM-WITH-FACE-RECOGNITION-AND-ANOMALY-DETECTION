# HƯỚNG DẪN CẮM DÂY VÀ KẾT NỐI PHẦN CỨNG RASPBERRY PI 4

Tài liệu này hướng dẫn chi tiết cách cắm các cổng kết nối ngoại vi, nguồn cấp và mạng LAN trên bo mạch **Raspberry Pi 4 Model B** để tạo thành một nút biên (Edge Node) AI hoàn chỉnh kết nối với máy tính cá nhân (Laptop) và Camera.

---

## 1. Sơ đồ kết nối phần cứng (ASCII Diagram)

```text
               +----------------------------------------------------+
               |                RASPBERRY PI 4 MODEL B              |
               |                                                    |
  [Quạt 5V] --->| [GPIO Pins]  (Cắm chân Đỏ -> chân 4, Đen -> chân 6)
 [Cảm biến Ga]->|              (VCC -> chân 2 (5V), GND -> chân 9, DO -> chân 12 (GPIO 18))
 [Khóa/Rơ-le] ->|              (VCC -> chân 4 (5V) chia sẻ, GND -> chân 14, IN -> chân 16 (GPIO 23))
 [Còi báo động]->|             (VCC -> chân 2 (5V) chia sẻ, GND -> chân 14 chia sẻ, IN -> chân 18 (GPIO 24))
                |                                                    |
 [Nguồn USB-C] | [USB-C Port] (Nguồn cấp chính hãng 5V-3A)          |
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

## 2. Hướng dẫn cắm dây từng bước

### Bước 1: Cài đặt thẻ nhớ MicroSD
* Đảm bảo thẻ nhớ MicroSD đã được flash hệ điều hành (Raspberry Pi OS hoặc Ubuntu Server).
* Cắm thẻ nhớ vào khe cắm thẻ nhớ ở **mặt dưới** của bo mạch Raspberry Pi 4 (lưu ý cắm đúng chiều mặt đồng quay về phía mạch).

### Bước 2: Lắp quạt tản nhiệt (Active Cooler)
* Dán các miếng truyền nhiệt (Thermal Pad) lên chip CPU, RAM và chip quản lý nguồn của Pi.
* Đặt quạt tản nhiệt lên và cắm dây cấp nguồn cho quạt vào chân GPIO ở hàng chân cắm:
  * **Dây màu Đỏ (Cực dương 5V)**: Cắm vào **Chân số 4** (Hàng ngoài, chân thứ 2 tính từ bên trái sang).
  * **Dây màu Đen (Cực âm GND)**: Cắm vào **Chân số 6** (Hàng ngoài, chân thứ 3 tính từ bên trái sang).
  *(Lưu ý: Nếu quạt có jack cắm 3 chân/4 chân chuyên dụng và vỏ case hỗ trợ, hãy cắm đúng theo khe hướng dẫn).*

### Bước 3: Cắm USB Webcam
* Bạn cắm cổng kết nối của USB Webcam vào một trong hai cổng **USB 3.0 (Cổng có lõi nhựa màu xanh dương)** trên Raspberry Pi 4.
* *Tại sao cần cắm cổng USB 3.0?* Cổng USB 3.0 có băng thông truyền tải dữ liệu hình ảnh lớn hơn nhiều so với cổng USB 2.0 (màu đen), giúp giảm độ trễ truyền khung hình từ webcam vào mô hình AI xử lý.

### Bước 4: Kết nối mạng (Mạng LAN hoặc Wi-Fi)
* **Cách 1 (Khuyên dùng khi báo cáo)**: Cắm một đầu cáp mạng LAN (RJ45) vào cổng **Ethernet** của Raspberry Pi 4, đầu còn lại cắm vào bộ **Router Wi-Fi** hoặc **Switch**. Máy tính cá nhân (Laptop) của bạn cũng kết nối vào cục Router Wi-Fi này để tạo thành một mạng nội bộ (LAN).
* **Cách 2 (Không dây)**: Nếu không có cáp mạng, bạn cấu hình kết nối Wi-Fi cho Raspberry Pi 4 kết nối cùng mạng Wi-Fi với Laptop.

### Bước 5: Cắm màn hình điều khiển (Tùy chọn)
* Nếu bạn muốn nhìn trực tiếp màn hình Desktop của Pi để cấu hình, hãy cắm cáp **Micro-HDMI** vào cổng HDMI sát cổng nguồn USB-C của Pi, đầu còn lại cắm vào cổng HDMI của màn hình máy tính/TV.

### Bước 6: Cắm nguồn điện USB-C
* Cắm đầu dây USB-C của củ nguồn điện chính hãng (5V-3A) vào cổng nguồn **USB-C** trên Pi.
* Cắm củ nguồn vào ổ điện gia đình. Raspberry Pi 4 sẽ tự động khởi động (đèn đỏ sáng liên tục, đèn xanh lá nhấp nháy báo đọc thẻ nhớ).

### Bước 7: Cắm cảm biến khí ga MQ-2 (hoặc MQ-5)
Để mở rộng hệ thống giám sát rò rỉ khí ga phòng bếp (tác vụ an toàn bổ sung), bạn nối 3 dây từ cảm biến MQ-2 vào hàng chân GPIO của Raspberry Pi 4:
* **Chân VCC (Nguồn 5V)**: Nối vào **Chân số 2** (Hàng ngoài, chân đầu tiên bên trái) trên Pi 4 để lấy nguồn 5V.
* **Chân GND (Đất)**: Nối vào **Chân số 9** (Hàng trong, chân thứ 5 từ bên trái sang) hoặc bất kỳ chân GND nào của Pi.
* **Chân DO (Digital Output)**: Nối vào **Chân số 12 (GPIO 18)** trên Pi 4 để truyền tín hiệu cảnh báo số.
* *Cách căn chỉnh cảm biến*: Trên mạch MQ-2 có sẵn một núm xoay biến trở màu xanh dương. Bạn cắm điện vào Pi, dùng tuốc nơ vít nhỏ xoay nhẹ núm này sao cho trong điều kiện không khí thường đèn LED cảnh báo tắt, và khi bạn xịt nhẹ bật lửa (không đánh lửa) có gas vào đầu cảm biến, đèn LED lập tức sáng lên. Hệ thống sẽ tự động bắt mức tín hiệu này và kích hoạt còi cảnh báo + gửi tin Telegram trong vòng 1 giây.

### Bước 8: Cắm Rơ-le (Relay) để điều khiển mở Khóa cửa điện từ (Solenoid Lock)
Để kích hoạt tính năng mở cửa từ xa (bấm nút trên Telegram hoặc Web Dashboard), bạn kết nối module Rơ-le 5V điều khiển khóa từ vào Raspberry Pi 4 như sau:
* **Chân VCC (Nguồn 5V)**: Nối vào **Chân số 4** (Hàng ngoài, chân thứ 2 từ bên trái) trên hàng GPIO của Pi (bạn có thể dùng jack chia 5V hoặc nối chung với chân nguồn của Quạt 5V).
* **Chân GND (Đất)**: Nối vào **Chân số 14** (Hàng ngoài, chân thứ 7 từ bên trái) hoặc bất kỳ chân Ground trống nào trên Pi.
* **Chân IN (Tín hiệu điều khiển)**: Nối vào **Chân số 16 (GPIO 23)** trên Pi 4.
* **Đầu ra Relay (Cổng COM và NO)**: Đấu nối tiếp với nguồn cấp độc lập của khóa Solenoid (thường là nguồn tổ ong 12V-2A hoặc pin ngoài). Khi có lệnh mở cửa từ Telegram/Web, Pi sẽ xuất mức HIGH lên chân GPIO 23, hút cuộn dây Rơ-le làm thông mạch COM-NO để cấp điện mở khóa cửa trong 3 giây rồi tự động khóa lại.

### Bước 9: Cắm Còi báo động vật lý (Active Buzzer 5V)
Để hệ thống có thể hú còi báo động vật lý tại chỗ khi phát hiện hỏa hoạn, rò rỉ khí ga, hoặc có xâm nhập khi khóa nhà, bạn kết nối còi báo động 5V vào Raspberry Pi 4 như sau:
* **Chân VCC (Nguồn 5V)**: Nối vào **Chân số 2** (Hàng ngoài, chân thứ 1 từ bên trái) - đấu song song chia sẻ với VCC của cảm biến Ga.
* **Chân GND (Đất)**: Nối vào **Chân số 14** (Hàng ngoài, chân thứ 7 từ bên trái) - đấu song song chia sẻ với GND của module Rơ-le.
* **Chân I/O (Tín hiệu điều khiển)**: Nối vào **Chân số 18 (GPIO 24)** trên Pi 4.
* **Cơ chế hoạt động**: Khi hệ thống báo động kích hoạt, Pi sẽ xuất tín hiệu HIGH/LOW liên tục để hú còi theo nhịp:
  * *Báo cháy (Fire)*: Nhấp nháy còi cực nhanh (0.1 giây ON, 0.1 giây OFF).
  * *Rò rỉ khí Ga (Gas)*: Nhấp nháy còi chu kỳ vừa (0.3 giây ON, 0.3 giây OFF).
  * *Khóa nhà có xâm nhập (Intrusion)*: Nhấp nháy còi chu kỳ chậm (0.8 giây ON, 0.8 giây OFF).

---

## 3. Cách tìm địa chỉ IP của Raspberry Pi để kết nối từ Laptop

Khi Raspberry Pi 4 khởi động và nhận mạng từ Router, nó sẽ được cấp một địa chỉ IP nội bộ (ví dụ: `192.168.1.15`). Để kết nối từ Laptop vào Pi qua SSH hoặc Web, bạn cần biết IP này:

1. **Cách 1 (Dùng phần mềm quét IP)**: Tải phần mềm **Advanced IP Scanner** (miễn phí) trên Laptop $\rightarrow$ Nhấn **Scan** $\rightarrow$ Tìm thiết bị có tên nhà sản xuất là `Raspberry Pi Foundation` để lấy địa chỉ IP.
2. **Cách 2 (Xem trong trang cấu hình Router)**: Đăng nhập vào trang quản trị của Router Wi-Fi (thường là `192.168.1.1` hoặc `192.168.0.1`) $\rightarrow$ Xem danh sách thiết bị kết nối (DHCP Client List) để tìm địa chỉ IP của Raspberry Pi.
3. **Cách 3 (Dùng màn hình)**: Nếu có cắm màn hình HDMI vào Pi ở Bước 5, bạn chỉ cần mở Terminal trên Pi và gõ lệnh:
   ```bash
   hostname -I
   ```
   Địa chỉ IP sẽ hiển thị ngay trên màn hình.
