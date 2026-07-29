import time
import sys

print("==================================================")
print("   CHUONG TRINH KIEM TRA PHAN CUNG TRUC TIEP      ")
print("==================================================")

try:
    import RPi.GPIO as GPIO
    has_gpio = True
except ImportError:
    print("[CANH BAO] Khong tim thay thu vien RPi.GPIO!")
    print("Script nay can duoc chay truc tiep tren Raspberry Pi de test GPIO.")
    print("Dang chay o che do mo phong gia lap tren may tinh...")
    has_gpio = False

# Cau hinh chan GPIO (Su dung he chan BCM)
BUZZER_PIN = 24  # Coi bao dong (GPIO 24 - Pin 18 vat ly)
LIGHT_PIN = 22   # Ro-le den (GPIO 22 - Pin 15 vat ly)

if has_gpio:
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(LIGHT_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(LIGHT_PIN, GPIO.LOW)

def test_buzzer():
    print("\n>>> BAT DAU TEST COI (GPIO 24 - Pin 18) <<<")
    print("Coi se BAT 1 giay va TAT 1 giay (lap lai 5 lan)...")
    for i in range(5):
        print(f"Lan {i+1}/5: Coi BAT (HIGH)")
        if has_gpio:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(1.0)
        
        print(f"Lan {i+1}/5: Coi TAT (LOW)")
        if has_gpio:
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(1.0)
    print(">>> KET THUC TEST COI <<<")

def test_light():
    print("\n>>> BAT DAU TEST RO-LE DEN (GPIO 22 - Pin 15) <<<")
    print("Neu la Ro-le Active Low, trang thai kich hoat se nguoc lai.")
    print("Ro-le se BAT 2 giay va TAT 2 giay (lap lai 3 lan)...")
    for i in range(3):
        print(f"Lan {i+1}/3: Den BAT (HIGH / Kich hoat)")
        if has_gpio:
            GPIO.output(LIGHT_PIN, GPIO.HIGH)
        time.sleep(2.0)
        
        print(f"Lan {i+1}/3: Den TAT (LOW / Ngat)")
        if has_gpio:
            GPIO.output(LIGHT_PIN, GPIO.LOW)
        time.sleep(2.0)
    print(">>> KET THUC TEST DEN <<<")

try:
    while True:
        print("\nChon thiet bi muon test:")
        print("1. Test Coi (Buzzer)")
        print("2. Test Den (Light Relay)")
        print("3. Thoat chuong trinh")
        choice = input("Nhap lua chon cua ban (1-3): ").strip()
        
        if choice == '1':
            test_buzzer()
        elif choice == '2':
            test_light()
        elif choice == '3':
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
