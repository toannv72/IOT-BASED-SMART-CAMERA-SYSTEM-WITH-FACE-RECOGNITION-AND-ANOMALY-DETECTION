import time
import sys

print("==================================================")
print("   CHUONG TRINH KIEM TRA PHAN CUNG TRUC TIEP      ")
print("==================================================")

try:
    import RPi.GPIO as GPIO
    has_gpio = True
except (ImportError, Exception) as e:
    print(f"[CANH BAO] Khong tim thay thu vien RPi.GPIO ({e})!")
    print("Script nay can duoc chay truc tiep tren Raspberry Pi de test GPIO.")
    print("Dang chay o che do mo phong gia lap...")
    if sys.platform.startswith("linux"):
        print("[HUONG DAN] De cai dat RPi.GPIO tren Raspberry Pi:")
        print("            pip install RPi.GPIO")
    has_gpio = False

# Cau hinh chan GPIO (Su dung he chan BCM)
BUZZER_PIN = 24  # Coi bao dong (GPIO 24 - Pin 18 vat ly)
LIGHT_PIN  = 22  # Ro-le den (GPIO 22 - Pin 15 vat ly)
GAS_PIN    = 18  # Cam bien Gas MQ-2 (GPIO 18 - Pin 12 vat ly)

if has_gpio:
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(LIGHT_PIN, GPIO.OUT)
    GPIO.setup(GAS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(LIGHT_PIN, GPIO.LOW)
    print("[THONG TIN] Da khoi tao RPi.GPIO (BCM mode) thanh cong.")
    print("[LUU Y] Neu he thong chinh (main.py / smartcamera.service) dang chay ngam,")
    print("        hay tam dung de tranh xung dot GPIO: sudo systemctl stop smartcamera.service\n")

def test_buzzer():
    print("\n>>> BAT DAU TEST COI (GPIO 24 - Pin 18) <<<")
    print("Coi se BAT 0.5 giay va TAT 0.5 giay (lap lai 5 lan)...")
    for i in range(5):
        print(f"Lan {i+1}/5: Coi BAT (HIGH - 3.3V)")
        if has_gpio:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.5)
        
        print(f"Lan {i+1}/5: Coi TAT (LOW - 0V)")
        if has_gpio:
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.5)
    print(">>> KET THUC TEST COI <<<\n")

def test_light():
    print("\n>>> BAT DAU TEST DEN / RO-LE (GPIO 22 - Pin 15) <<<")
    print("Thử nghiệm 1: Mức HIGH (Dành cho LED hoặc Rơ-le Active High)...")
    for i in range(2):
        print(f"  [HIGH] Bật trong 2 giây...")
        if has_gpio:
            GPIO.output(LIGHT_PIN, GPIO.HIGH)
        time.sleep(2.0)
        print(f"  [LOW] Tắt trong 1 giây...")
        if has_gpio:
            GPIO.output(LIGHT_PIN, GPIO.LOW)
        time.sleep(1.0)
        
    print("\nThử nghiệm 2: Mức LOW (Dành cho Module Rơ-le kích mức Thấp / Active Low)...")
    print("  [LOW] Kích hoạt rơ-le trong 2 giây...")
    if has_gpio:
        GPIO.output(LIGHT_PIN, GPIO.LOW)
    time.sleep(2.0)
    print("  [HIGH] Ngắt rơ-le...")
    if has_gpio:
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
    time.sleep(1.0)
    if has_gpio:
        GPIO.output(LIGHT_PIN, GPIO.LOW)
    print(">>> KET THUC TEST DEN <<<\n")

def test_gas_sensor():
    print("\n>>> BAT DAU DOC TRUC TIEP CAM BIEN KHI GA MQ-2 (GPIO 18 - Pin 12) <<<")
    print("Hệ thống sẽ đọc trạng thái chân DO mỗi 0.5 giây trong vòng 10 giây.")
    print("Mẹo: Dùng bật lửa ga xịt nhẹ vào đầu cảm biến hoặc dùng tuốc nơ vít xoay chiết áp xanh.")
    print("Trạng thái DO chuẩn: HIGH (1) = Sạch / Bình thường | LOW (0) = PHÁT HIỆN RÒ RỈ GA\n")
    
    start_t = time.time()
    while time.time() - start_t < 10.0:
        elapsed = int(time.time() - start_t)
        if has_gpio:
            val = GPIO.input(GAS_PIN)
            status = "🚨 PHÁT HIỆN KHÍ GA (LOW/0)" if val == GPIO.LOW else "🟢 KHÔNG KHÍ SẠCH (HIGH/1)"
            print(f"[{elapsed:02d}s] Giá trị chân DO: {val} -> {status}")
        else:
            print(f"[{elapsed:02d}s] [SIMULATION] Chân DO = 1 -> 🟢 KHÔNG KHÍ SẠCH (Giả lập máy dev)")
        time.sleep(0.5)
    print(">>> KET THUC TEST CAM BIEN GA <<<\n")

try:
    while True:
        print("--------------------------------------------------")
        print("Chon thiet bi muon test:")
        print("1. Test Coi bao dong (Buzzer - GPIO 24)")
        print("2. Test Ro-le Den / LED (GPIO 22)")
        print("3. Test Cam bien khi Ga MQ-2 doc truc tiep (GPIO 18)")
        print("4. Thoat chuong trinh")
        print("--------------------------------------------------")
        choice = input("Nhap lua chon cua ban (1-4): ").strip()
        
        if choice == '1':
            test_buzzer()
        elif choice == '2':
            test_light()
        elif choice == '3':
            test_gas_sensor()
        elif choice == '4':
            print("Dang thoat va don dep GPIO...")
            if has_gpio:
                GPIO.cleanup()
            break
        else:
            print("Lua chon khong hop le, vui long chon lai!")
except KeyboardInterrupt:
    print("\nDa huy chuong trinh. Dang don dep GPIO...")
    if has_gpio:
        GPIO.cleanup()
