import sys
import uvicorn
import threading
import webbrowser
import time
import socket

# Cấu hình lại mã hóa UTF-8 cho stdout/stderr để tránh lỗi UnicodeEncodeError trên Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

def wait_for_port_to_be_free(port=8000, host="0.0.0.0", retries=15):
    for i in range(retries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except socket.error:
                # Cổng đang bị chiếm dụng hoặc trong trạng thái TIME_WAIT giải phóng chậm trên Windows
                print(f"[SYSTEM] Cổng {port} đang bận (chờ giải phóng hoặc đang khởi động tiến trình mới). Đang thử lại ({i+1}/{retries})...")
                time.sleep(1.5)
    return False

def start_browser():
    # Đợi server uvicorn khởi động lên khoảng 2 giây rồi tự mở Dashboard
    time.sleep(2.0)
    print("======================================================================")
    print("[SYSTEM] Đang tự động mở trình duyệt truy cập: http://localhost:8000")
    print("======================================================================")
    webbrowser.open("http://localhost:8000")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    # Đảm bảo cổng 8000 rảnh trước khi nạp mô hình nặng và khởi chạy uvicorn
    if not wait_for_port_to_be_free(port=8000, host="0.0.0.0"):
        print("[SYSTEM] Lỗi: Cổng 8000 đang bị chiếm hoàn toàn bởi ứng dụng khác. Vui lòng tắt ứng dụng đó trước.")
        sys.exit(1)
        
    local_ip = get_local_ip()
    print("======================================================================")
    print("[SYSTEM] HỆ THỐNG SMART CAMERA BIÊN ĐÃ KHỞI CHẠY THÀNH CÔNG!")
    print(f" 👉 LINK TRUY CẬP TRÊN THIẾT BỊ NÀY: http://localhost:8000")
    print(f" 👉 LINK TRUY CẬP TỪ THIẾT BỊ KHÁC TRONG MẠNG WI-FI: http://{local_ip}:8000")
    print("======================================================================")
        
    # Khởi chạy luồng mở trình duyệt song song (Tạm tắt để tránh lỗi tự động tắt trên terminal Windows/VSCode)
    # threading.Thread(target=start_browser, daemon=True).start()
    
    # Chạy Uvicorn ASGI Server nạp ứng dụng từ package 'app'
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
