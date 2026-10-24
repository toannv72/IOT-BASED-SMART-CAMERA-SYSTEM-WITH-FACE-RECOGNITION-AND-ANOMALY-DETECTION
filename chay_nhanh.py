"""
=============================================================================
HỆ THỐNG SMART CAMERA EDGE AI - KHỞI CHẠY NHANH 1 NÚT (WINDOWS)
=============================================================================
"""
import os
import sys
import time
import subprocess
import webbrowser
import threading

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def free_port(port=8000):
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
    except Exception:
        pass

def main():
    print("="*65)
    print("       HỆ THỐNG SMART CAMERA EDGE AI - CHẾ ĐỘ CHẠY 1 NÚT")
    print("="*65)
    print("[*] Đang giải phóng cổng 8000 nếu bị kẹt tiến trình cũ...")
    free_port(8000)
    
    print("[*] Đang tự động mở trình duyệt web sau 2.5 giây...")
    def open_browser():
        time.sleep(2.5)
        webbrowser.open("http://localhost:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("[*] Đang khởi chạy máy chủ Smart Camera...")
    print("[*] Địa chỉ truy cập Dashboard: http://localhost:8000")
    print("="*65 + "\n")
    
    os.chdir(PROJECT_DIR)
    subprocess.run([sys.executable, "main.py"])

if __name__ == "__main__":
    main()
