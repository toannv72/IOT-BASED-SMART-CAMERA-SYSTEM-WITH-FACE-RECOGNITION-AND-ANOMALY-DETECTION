import sys
import uvicorn
import threading
import webbrowser
import time

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

def start_browser():
    # Đợi server uvicorn khởi động lên khoảng 2 giây rồi tự mở Dashboard
    time.sleep(2.0)
    print("======================================================================")
    print("[SYSTEM] Đang tự động mở trình duyệt truy cập: http://localhost:8000")
    print("======================================================================")
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Khởi chạy luồng mở trình duyệt song song
    threading.Thread(target=start_browser, daemon=True).start()
    
    # Chạy Uvicorn ASGI Server nạp ứng dụng từ package 'app'
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
