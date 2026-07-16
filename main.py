import sys
import uvicorn
import threading
import webbrowser
import time
import socket

# Cấu hình lại mã hóa UTF-8 cho stdout/stderr để tránh lỗi UnicodeEncodeError trên Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
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

if __name__ == "__main__":
    # Đảm bảo cổng 8000 rảnh trước khi nạp mô hình nặng và khởi chạy uvicorn
    if not wait_for_port_to_be_free(port=8000, host="0.0.0.0"):
        print("[SYSTEM] Lỗi: Cổng 8000 đang bị chiếm hoàn toàn bởi ứng dụng khác. Vui lòng tắt ứng dụng đó trước.")
        sys.exit(1)
        
    # Khởi chạy luồng mở trình duyệt song song (Tạm tắt để tránh lỗi tự động tắt trên terminal Windows/VSCode)
    # threading.Thread(target=start_browser, daemon=True).start()
    
    # Chạy Uvicorn ASGI Server nạp ứng dụng từ package 'app'
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
