"""
=============================================================================
TRÌNH CÀI ĐẶT ỨNG DỤNG SMART CAMERA AI - TỰ KHỞI ĐỘNG CÙNG WINDOWS
=============================================================================
"""
import os
import sys
import time
import subprocess
import webbrowser

# Cấu hình UTF-8 cho console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_BAT = os.path.join(PROJECT_DIR, "CHAY_1_NUT.bat")

def print_banner():
    print("="*70)
    print("   TRÌNH CÀI ĐẶT ỨNG DỤNG SMART CAMERA AI - TỰ KHỞI ĐỘNG (WINDOWS)   ")
    print("="*70)
    print(" Mục tiêu: Biến hệ thống thành Ứng dụng tự động khởi chạy 100%:")
    print("  ✔ Tự động bật lên mỗi khi bạn mở máy tính hoặc khi có điện lại.")
    print("  ✔ Tạo biểu tượng ứng dụng 'Smart Camera AI' ngay trên Desktop.")
    print("  ✔ Tự động giải phóng cổng 8000 và kết nối camera.")
    print("-" * 70)

def free_port(port=8000):
    """Giải phóng cổng mạng nếu đang bị chiếm dụng"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.net_connections(kind='inet'):
                    if conn.laddr.port == port:
                        print(f"[*] Đang giải phóng cổng {port} từ tiến trình {proc.info['name']} (PID: {proc.info['pid']})...")
                        proc.kill()
            except Exception:
                pass
    except Exception as e:
        # Fallback bằng lệnh netstat / taskkill
        try:
            cmd = f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /f /pid %a'
            subprocess.run(cmd, shell=True, capture_output=True)
        except Exception:
            pass

def create_windows_shortcut(target, shortcut_path, working_dir, desc="Smart Camera AI"):
    """Tạo shortcut .lnk bằng PowerShell"""
    try:
        ps_code = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.WorkingDirectory = "{working_dir}"; '
            f'$s.Description = "{desc}"; '
            f'$s.Save()'
        )
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True)
        if os.path.exists(shortcut_path):
            return True
        else:
            return False
    except Exception as e:
        print(f"[!] Lỗi tạo shortcut: {e}")
        return False

def main():
    print_banner()
    
    # 1. Thư mục Startup của Windows
    appdata = os.environ.get('APPDATA', '')
    startup_dir = os.path.join(appdata, r'Microsoft\Windows\Start Menu\Programs\Startup')
    startup_lnk = os.path.join(startup_dir, 'Smart Camera AI.lnk')
    
    # 2. Thư mục Desktop của User
    userprofile = os.environ.get('USERPROFILE', '')
    desktop_dir = os.path.join(userprofile, 'Desktop')
    desktop_lnk = os.path.join(desktop_dir, 'Smart Camera AI.lnk')
    
    print("\n[*] Đang tạo biểu tượng ứng dụng...")
    
    # Tạo shortcut Startup
    if os.path.exists(startup_dir):
        ok_startup = create_windows_shortcut(TARGET_BAT, startup_lnk, PROJECT_DIR, "Smart Camera AI Auto-Start")
        if ok_startup:
            print(f" ✔ Đã cài đặt tự khởi động cùng Windows:")
            print(f"   -> {startup_lnk}")
        else:
            print(" [!] Không thể tạo shortcut trong thư mục Startup.")
    
    # Tạo shortcut Desktop
    if os.path.exists(desktop_dir):
        ok_desktop = create_windows_shortcut(TARGET_BAT, desktop_lnk, PROJECT_DIR, "Smart Camera AI Desktop Launcher")
        if ok_desktop:
            print(f" ✔ Đã tạo biểu tượng ứng dụng ngoài màn hình chính (Desktop):")
            print(f"   -> {desktop_lnk}")
    
    print("\n" + "="*70)
    print("  [THÀNH CÔNG] ĐÃ CÀI ĐẶT SMART CAMERA THÀNH ỨNG DỤNG TỰ CHẠY!")
    print("="*70)
    print(" Từ nay:")
    print(" 1. Mỗi khi BẬT MÁY TÍNH hoặc khi MẤT ĐIỆN CÓ ĐIỆN LẠI:")
    print("    -> Smart Camera sẽ TỰ ĐỘNG CHẠY NGAY mà bạn không cần phải mở thủ công!")
    print(" 2. Ngoài màn hình Desktop đã có sẵn biểu tượng 'Smart Camera AI':")
    print("    -> Nhấp đúp vào bất kỳ lúc nào để khởi chạy hoặc mở Dashboard!")
    print("="*70)
    
    # Giải phóng port 8000
    free_port(8000)
    
    print("\n[*] Đang tự động khởi chạy Smart Camera ngay bây giờ...")
    time.sleep(1.5)
    
    # Tự động mở trình duyệt sau 3 giây
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8000")
        
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Khởi chạy main.py
    os.chdir(PROJECT_DIR)
    subprocess.run([sys.executable, "main.py"])

if __name__ == "__main__":
    main()
