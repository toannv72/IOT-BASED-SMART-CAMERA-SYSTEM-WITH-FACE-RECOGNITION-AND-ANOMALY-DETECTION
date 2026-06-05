import os
import cv2
import time
import json
import requests
import threading
from datetime import datetime, timedelta
from app.config import settings
from app.database import SessionLocal, SystemEventLog

# Quản lý thời gian gửi cảnh báo trước đó để tính Cooldown tránh gửi lặp
last_alert_times = {}
alert_lock = threading.Lock()

def sanitize_filename_component(text):
    # Vietnamese character mapping to ASCII
    co_dau = "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ "
    khong_dau = "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyydAAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD_"
    char_map = str.maketrans(co_dau, khong_dau)
    translated = text.translate(char_map)
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', translated)
    return sanitized

def send_telegram_alert(message, frame, alert_type="intrusion", camera_id="Unknown", frame_buffer=None, face_name=None):
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
    if face_name:
        cooldown_key = f"{alert_type}_{camera_id}_{face_name}"
        
    with alert_lock:
        last_time = last_alert_times.get(cooldown_key, 0)
        if current_time - last_time < cooldown:
            return
        last_alert_times[cooldown_key] = current_time
        
    # Tạo bản sao của khung hình để tránh xung đột ghi đè giữa luồng xử lý và luồng gửi tin
    frame_copy = frame.copy()
    
    # Tạo bản sao sâu của frame_buffer nếu có
    buffer_copy = [f.copy() for f in frame_buffer] if frame_buffer else None
    
    def send_worker():
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        sanitized_cam = sanitize_filename_component(camera_id)
        img_filename = f"alert_{alert_type}_{sanitized_cam}_{timestamp_str}.jpg"
        img_local_path = os.path.join("static", "alerts", img_filename)
        img_web_path = f"/static/alerts/{img_filename}"
        
        # 1. Lưu ảnh chụp sự kiện cục bộ
        try:
            cv2.imwrite(img_local_path, frame_copy)
            print(f"[ALERTS] Đã lưu ảnh chụp sự kiện cục bộ tại: {img_local_path}")
        except Exception as e:
            print(f"[ALERTS] Lỗi lưu ảnh chụp sự kiện: {e}")
            img_web_path = None
 
        # 2. Ghi video sự cố bất đồng bộ nếu có frame_buffer
        video_web_path = None
        if buffer_copy and len(buffer_copy) > 0:
            video_filename = f"alert_{alert_type}_{sanitized_cam}_{timestamp_str}.mp4"
            video_local_path = os.path.join("static", "alerts", video_filename)
            video_web_path = f"/static/alerts/{video_filename}"
            
            try:
                # Thiết lập VideoWriter (640x360, 15 FPS)
                # Thử mã hóa H.264 (avc1) trước để phát trực tiếp được trên các trình duyệt web
                fourcc = cv2.VideoWriter_fourcc(*'avc1')
                out = cv2.VideoWriter(video_local_path, fourcc, 15.0, (640, 360))
                
                # Nếu avc1 không được hỗ trợ (do thiếu codec trên HĐH), fallback về mp4v chuẩn
                if not out.isOpened():
                    print("[ALERTS] Trình ghi 'avc1' không thể khởi tạo. Đang chuyển sang codec 'mp4v' dự phòng...")
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(video_local_path, fourcc, 15.0, (640, 360))
                    
                for f in buffer_copy:
                    out.write(f)
                out.release()
                print(f"[ALERTS] Đã lưu video sự cố thành công tại: {video_local_path}")
            except Exception as e:
                print(f"[ALERTS] Lỗi ghi video sự cố: {e}")
                video_web_path = None
            
        # 3. Ghi sự kiện cùng đường dẫn ảnh và video vào cơ sở dữ liệu SQLite
        db = SessionLocal()
        try:
            log_entry = SystemEventLog(
                event_type=alert_type,
                message=message,
                camera_id=camera_id,
                image_path=img_web_path,
                video_path=video_web_path,
                face_name=face_name
            )
            db.add(log_entry)
            db.commit()
            print(f"[ALERTS] Đã lưu sự kiện '{alert_type}' của '{camera_id}' vào SQLite (Có video: {video_web_path is not None}).")
        except Exception as e:
            db.rollback()
            print(f"[ALERTS] Lỗi lưu log vào cơ sở dữ liệu: {e}")
        finally:
            db.close()
            
        # 4. Tiến hành gọi API Telegram để gửi tin nhắn kèm hình ảnh và nút bấm tương tác
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
            
            # Cấu hình nút bấm tương tác 2 chiều
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔕 Tắt Báo Động", "callback_data": "mute_alerts"},
                        {"text": f"⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{camera_id}_30"}
                    ]
                ]
            }
            
            for chat_id in chats:
                files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
                payload = {
                    "chat_id": chat_id,
                    "caption": message,
                    "reply_markup": json.dumps(reply_markup)
                }
                requests.post(url, data=payload, files=files, timeout=10)
                
            print(f"[TELEGRAM] Đã gửi hình ảnh cảnh báo kèm nút bấm tương tác đến {len(chats)} người dùng.")
        except Exception as e:
            print(f"[TELEGRAM] Lỗi gọi API gửi Telegram: {e}")

    # Khởi chạy luồng con daemon để không cản trở tiến trình chính
    threading.Thread(target=send_worker, daemon=True).start()


# =========================================================================
# LUỒNG LẮNG NGHE PHẢN HỒI 2 CHIỀU TỪ TELEGRAM BOT (LONG POLLING)
# =========================================================================
def telegram_polling_loop():
    time.sleep(5)  # Đợi hệ thống khởi chạy ổn định
    offset = 0
    last_token = None
    print("[TELEGRAM] Bắt đầu khởi chạy luồng Polling bot tương tác 2 chiều...")
    
    while True:
        token = settings.get("telegram_token")
        if not token or token == "YOUR_TELEGRAM_BOT_TOKEN" or token.strip() == "":
            # Bỏ qua nếu token mặc định giả lập hoặc trống
            time.sleep(15)
            continue
            
        # Nếu đổi token mới hoặc khởi chạy lần đầu với token thực, xóa webhook cũ để kích hoạt Long Polling
        if token != last_token:
            try:
                print(f"[TELEGRAM] Cấu hình bot nhận thấy token mới/thực tế. Đang xóa Webhook để nhận updates...")
                del_webhook_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
                res = requests.post(del_webhook_url, json={"drop_pending_updates": True}, timeout=10)
                if res.status_code == 200:
                    print("[TELEGRAM] Đã xóa Webhook và xóa sạch các bản tin cũ đang đợi trên Telegram.")
                last_token = token
            except Exception as e:
                print(f"[TELEGRAM] Lỗi khi xóa Webhook: {e}")
            
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        try:
            response = requests.get(url, params={"offset": offset, "timeout": 20}, timeout=25)
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        
                        # Xử lý sự kiện bấm nút inline
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            cb_data = cb["data"]
                            chat_id = cb["message"]["chat"]["id"]
                            message_id = cb["message"]["message_id"]
                            
                            response_text = ""
                            new_markup = None
                            
                            # Trích xuất camera_id từ markup hiện tại nếu có
                            camera_id = None
                            try:
                                markup = cb["message"].get("reply_markup", {})
                                for row in markup.get("inline_keyboard", []):
                                    for btn in row:
                                        data = btn.get("callback_data", "")
                                        if data.startswith("pause_"):
                                            parts = data.split("_")
                                            camera_id = "_".join(parts[1:-1])
                                            break
                                        elif data.startswith("resume_"):
                                            camera_id = data.split("resume_")[-1]
                                            break
                            except Exception:
                                pass

                            if cb_data == "mute_alerts":
                                settings["alerts_enabled"] = False
                                from app.config import save_settings, SystemStatus
                                save_settings()
                                SystemStatus.add_log("Telegram Bot: Đã tắt cảnh báo an ninh hệ thống.", "warning")
                                response_text = "🔕 Đã tắt cảnh báo an ninh hệ thống."
                                
                                keyboard = [
                                    [
                                        {"text": "🔔 Bật Lại Báo Động", "callback_data": "unmute_alerts"}
                                    ]
                                ]
                                if camera_id:
                                    keyboard[0].append({"text": "⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{camera_id}_30"})
                                new_markup = {"inline_keyboard": keyboard}
                                
                            elif cb_data == "unmute_alerts":
                                settings["alerts_enabled"] = True
                                from app.config import save_settings, SystemStatus
                                save_settings()
                                SystemStatus.add_log("Telegram Bot: Đã bật lại cảnh báo an ninh hệ thống.", "success")
                                response_text = "🔔 Đã bật lại cảnh báo an ninh hệ thống."
                                
                                keyboard = [
                                    [
                                        {"text": "🔕 Tắt Báo Động", "callback_data": "mute_alerts"}
                                    ]
                                ]
                                if camera_id:
                                    keyboard[0].append({"text": "⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{camera_id}_30"})
                                new_markup = {"inline_keyboard": keyboard}
                                
                            elif cb_data.startswith("pause_"):
                                parts = cb_data.split("_")
                                cam_id = "_".join(parts[1:-1])
                                duration = int(parts[-1])
                                
                                from app.processors import pause_camera_alerts
                                pause_camera_alerts(cam_id, duration)
                                response_text = f"⏸️ Đã tạm ngắt cảnh báo camera '{cam_id}' trong {duration} phút."
                                
                                new_markup = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "🔕 Tắt Báo Động", "callback_data": "mute_alerts"},
                                            {"text": "▶️ Bật Lại Cam", "callback_data": f"resume_{cam_id}"}
                                        ]
                                    ]
                                }
                                
                            elif cb_data.startswith("resume_"):
                                cam_id = cb_data.split("resume_")[-1]
                                
                                from app.processors import resume_camera_alerts
                                resume_camera_alerts(cam_id)
                                response_text = f"▶️ Đã bật lại cảnh báo camera '{cam_id}' thành công."
                                
                                new_markup = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "🔕 Tắt Báo Động", "callback_data": "mute_alerts"},
                                            {"text": f"⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{cam_id}_30"}
                                        ]
                                    ]
                                }
                                
                            # Phản hồi lại Telegram xác nhận bấm nút thành công
                            answer_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                            requests.post(answer_url, json={"callback_query_id": cb_id, "text": response_text}, timeout=5)
                            
                            # Cập nhật nhãn caption và nút bấm của bức ảnh
                            edit_url = f"https://api.telegram.org/bot{token}/editMessageCaption"
                            original_caption = cb["message"].get("caption", "")
                            if "\n\n👉 [Hệ Thống]" in original_caption:
                                original_caption = original_caption.split("\n\n👉 [Hệ Thống]")[0]
                                
                            edit_payload = {
                                "chat_id": chat_id,
                                "message_id": message_id,
                                "caption": original_caption + f"\n\n👉 [Hệ Thống] {response_text}"
                            }
                            if new_markup:
                                edit_payload["reply_markup"] = json.dumps(new_markup)
                                
                            requests.post(edit_url, json=edit_payload, timeout=5)
            else:
                # Nếu có lỗi (ví dụ: token sai) thì ghi nhận lỗi và tạm nghỉ
                print(f"[TELEGRAM] getUpdates trả về status code {response.status_code}: {response.text}")
                time.sleep(10)
        except Exception as e:
            print(f"[TELEGRAM] Lỗi trong luồng Polling: {e}")
            time.sleep(5)
        time.sleep(2)

# Khởi chạy luồng Polling ngầm
threading.Thread(target=telegram_polling_loop, daemon=True, name="TelegramBotPolling").start()
