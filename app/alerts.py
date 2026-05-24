import os
import cv2
import time
import requests
import threading
from datetime import datetime
from app.config import settings
from app.database import SessionLocal, SystemEventLog

# Quản lý thời gian gửi cảnh báo trước đó để tính Cooldown tránh gửi lặp
last_alert_times = {}
alert_lock = threading.Lock()

def send_telegram_alert(message, frame, alert_type="intrusion", camera_id="Unknown"):
    """
    Gửi tin nhắn cảnh báo chứa hình ảnh chụp được qua Telegram và lưu lại cơ sở dữ liệu.
    Hàm được thực thi hoàn toàn bất đồng bộ trên một luồng riêng để tránh đứng hình camera stream.
    """
    global last_alert_times
    
    # Kiểm tra xem tính năng cảnh báo có đang được kích hoạt hay không
    if not settings.get("alerts_enabled", True):
        return
        
    cooldown = settings.get("telegram_cooldown", 15)
    current_time = time.time()
    
    # Kiểm tra cooldown theo loại cảnh báo và theo mã camera
    cooldown_key = f"{alert_type}_{camera_id}"
    with alert_lock:
        last_time = last_alert_times.get(cooldown_key, 0)
        if current_time - last_time < cooldown:
            return
        last_alert_times[cooldown_key] = current_time
        
    # Tạo bản sao của khung hình để tránh xung đột ghi đè giữa luồng xử lý và luồng gửi tin
    frame_copy = frame.copy()
    
    def send_worker():
        # 1. Chụp ảnh khung hình hiện tại và lưu vào thư mục static/alerts/
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"alert_{alert_type}_{camera_id}_{timestamp_str}.jpg"
        local_path = os.path.join("static", "alerts", filename)
        web_path = f"/static/alerts/{filename}"
        
        try:
            cv2.imwrite(local_path, frame_copy)
            print(f"[ALERTS] Đã lưu ảnh chụp sự kiện cục bộ tại: {local_path}")
        except Exception as e:
            print(f"[ALERTS] Lỗi lưu ảnh chụp sự kiện: {e}")
            web_path = None
            
        # 2. Ghi sự kiện cùng đường dẫn ảnh vào cơ sở dữ liệu SQLite
        db = SessionLocal()
        try:
            log_entry = SystemEventLog(
                event_type=alert_type,
                message=message,
                camera_id=camera_id,
                image_path=web_path
            )
            db.add(log_entry)
            db.commit()
            print(f"[ALERTS] Đã lưu sự kiện '{alert_type}' của '{camera_id}' vào SQLite.")
        except Exception as e:
            db.rollback()
            print(f"[ALERTS] Lỗi lưu log vào cơ sở dữ liệu: {e}")
        finally:
            db.close()
            
        # 3. Tiến hành gọi API Telegram để gửi tin nhắn kèm hình ảnh
        token = settings.get("telegram_token")
        chats = settings.get("telegram_chats", [])
        
        if not token or not chats:
            print("[ALERTS] Thiếu token hoặc chat ID Telegram. Bỏ qua việc gửi tin nhắn.")
            return
            
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            success, buffer = cv2.imencode(".jpg", frame_copy)
            if not success:
                return
                
            for chat_id in chats:
                files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
                payload = {"chat_id": chat_id, "caption": message}
                requests.post(url, data=payload, files=files, timeout=10)
                
            print(f"[TELEGRAM] Đã gửi hình ảnh cảnh báo đến {len(chats)} người dùng.")
        except Exception as e:
            print(f"[TELEGRAM] Lỗi gọi API gửi Telegram: {e}")

    # Khởi chạy luồng con daemon để không cản trở tiến trình chính
    threading.Thread(target=send_worker, daemon=True).start()
