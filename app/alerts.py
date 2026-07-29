import os
import cv2
import time
import json
import requests
import threading
from datetime import datetime, timedelta
from app.config import settings, SystemStatus
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

def get_alert_keyboard(chat_id, camera_id=None, is_paused=False):
    """
    Tạo cấu hình bàn phím Inline đồng nhất cho các cảnh báo gửi qua Telegram
    """
    from app.config import SystemStatus, settings
    
    # Xác định trạng thái câm hiện tại cho riêng user này
    muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
    is_muted = chat_id in muted_chats
    mute_text = "🔔 Bật Lại Báo Động" if is_muted else "🔕 Tắt Báo Động"
    mute_cb = "unmute_alerts" if is_muted else "mute_alerts"
    
    keyboard = []
    
    # Dòng 1: Điều khiển tắt còi vật lý tạm thời
    is_buzzer_muted = time.time() < getattr(SystemStatus, "buzzer_mute_until", 0.0)
    if is_buzzer_muted:
        keyboard.append([{"text": "🔊 Bật Lại Còi Báo Động", "callback_data": "unmute_buzzer"}])
    else:
        keyboard.append([
            {"text": "🔇 Tắt Còi 30p", "callback_data": "mute_buzzer_30"},
            {"text": "🔇 Tắt Còi 1h", "callback_data": "mute_buzzer_60"}
        ])
        
    # Dòng 2: Tắt nhận thông báo cho user hiện tại & Tạm dừng camera
    row2 = [{"text": mute_text, "callback_data": mute_cb}]
    if camera_id and camera_id != "Unknown":
        if is_paused:
            row2.append({"text": "▶️ Bật Lại Cam", "callback_data": f"resume_{camera_id}"})
        else:
            row2.append({"text": f"⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{camera_id}_30"})
    keyboard.append(row2)
    
    # Dòng 3: Bật/Tắt đèn & Test phần cứng
    keyboard.append([
        {"text": "💡 Bật/Tắt Đèn", "callback_data": "toggle_light"}
    ])
    keyboard.append([
        {"text": "🔊 Test Còi 3s", "callback_data": "test_buzzer_3s"},
        {"text": "💡 Test Đèn 5s", "callback_data": "test_light_5s"}
    ])
    
    return {"inline_keyboard": keyboard}

def send_telegram_alert(message, frame, alert_type="intrusion", camera_id="Unknown", frame_buffer=None, face_name=None):
    """
    Gửi tin nhắn cảnh báo chứa hình ảnh chụp được qua Telegram và lưu lại cơ sở dữ liệu.
    Hàm được thực thi hoàn toàn bất đồng bộ trên một luồng riêng để tránh đứng hình camera stream.
    """
    global last_alert_times
    
    # Kiểm tra xem tính năng cảnh báo có đang được kích hoạt hay không
    # Nếu là cảnh báo nguy hiểm thì bỏ qua kiểm tra công tắc tắt cảnh báo chung
    unmutable_alerts = settings.get("unmutable_alerts", ["fire", "gas"])
    if not settings.get("alerts_enabled", True) and alert_type not in unmutable_alerts:
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
        
    # Kích hoạt tự động bật đèn nếu phát hiện xâm nhập vùng cấm
    if alert_type == "intrusion":
        try:
            from app.processors import trigger_auto_light
            duration = settings.get("light_auto_off_seconds", 30)
            trigger_auto_light(duration, frame)
        except Exception as err:
            print(f"[LIGHT RELAY] Lỗi tự động kích hoạt đèn: {err}")
        
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
        chats = [str(x) for x in settings.get("telegram_chats", [])]
        muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
        
        if not token or not chats:
            print("[ALERTS] Thiếu token hoặc chat ID Telegram. Bỏ qua việc gửi tin nhắn.")
            return
            
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            success, buffer = cv2.imencode(".jpg", frame_copy)
            if not success:
                return
            
            sent_count = 0
            for chat_id in chats:
                # Nếu người dùng này đã tắt nhận cảnh báo, và loại cảnh báo có thể tắt (không nằm trong danh sách không thể tắt)
                if chat_id in muted_chats and alert_type not in unmutable_alerts:
                    continue
                
                # Cấu hình nút bấm tương tác 2 chiều động dùng hàm dùng chung
                reply_markup = get_alert_keyboard(chat_id, camera_id)
                
                files = {"photo": ("alert.jpg", buffer.tobytes(), "image/jpeg")}
                payload = {
                    "chat_id": chat_id,
                    "caption": message,
                    "reply_markup": json.dumps(reply_markup)
                }
                requests.post(url, data=payload, files=files, timeout=10)
                sent_count += 1
                
            print(f"[TELEGRAM] Đã gửi hình ảnh cảnh báo kèm nút bấm tương tác đến {sent_count} người dùng (bỏ qua {len(chats) - sent_count} người đã tắt).")
        except Exception as e:
            print(f"[TELEGRAM] Lỗi gọi API gửi Telegram: {e}")

    # Khởi chạy luồng con daemon để không cản trở tiến trình chính
    threading.Thread(target=send_worker, daemon=True).start()


# =========================================================================
# LUỒNG LẮNG NGHE PHẢN HỒI 2 CHIỀU TỪ TELEGRAM BOT (LONG POLLING)
# =========================================================================
def send_camera_menu(token, chat_id, message_id=None):
    from app.config import get_cameras_config
    cameras = get_cameras_config()
    
    text = "🎥 *DANH SÁCH CAMERA AN NÌNH*\n\nChọn một camera dưới đây để Bật/Tắt (Arm/Disarm) cảnh báo an ninh của camera đó:"
    keyboard = []
    
    for cam in cameras:
        cam_id = cam["camera_id"]
        cam_name = cam.get("name", cam_id)
        is_armed = cam.get("alerts_enabled", True)
        
        status_str = "🟢 Đang bật" if is_armed else "🔴 Đang tắt"
        button_text = f"{cam_name}: {status_str}"
        keyboard.append([{"text": button_text, "callback_data": f"tg_cam_{cam_id}"}])
        
    keyboard.append([{"text": "🔄 Làm mới danh sách", "callback_data": "refresh_cam_menu"}])
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({"inline_keyboard": keyboard})
    }
    
    try:
        if message_id:
            payload["message_id"] = message_id
            edit_url = f"https://api.telegram.org/bot{token}/editMessageText"
            requests.post(edit_url, json=payload, timeout=5)
        else:
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(send_url, json=payload, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM] Lỗi khi gửi menu camera: {e}")
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
                        
                        # Xử lý tin nhắn văn bản (Text Commands)
                        if "message" in update and "text" in update["message"]:
                            msg = update["message"]
                            chat_id = str(msg["chat"]["id"])
                            txt = msg["text"].strip().lower()
                            if txt in ("/light_on", "bat den", "bật đèn", "bật đèn chiếu sáng"):
                                from app.processors import set_light_state
                                set_light_state(True)
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "💡 [ĐIỀU KHIỂN TỪ XA]\nĐã bật đèn chiếu sáng thông minh thành công."
                                }, timeout=5)
                            elif txt in ("/light_off", "tat den", "tắt đèn", "tắt đèn chiếu sáng"):
                                from app.processors import set_light_state
                                set_light_state(False)
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔌 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt đèn chiếu sáng thông minh thành công."
                                }, timeout=5)
                            elif txt in ("/cameras", "/cam", "/danh_sach_cam", "cameras", "cam"):
                                send_camera_menu(token, chat_id)
                            elif txt in ("/mute", "/tat_bao_dong", "tat bao dong", "tat_bao_dong"):
                                from app.config import save_settings
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id not in muted_chats:
                                    muted_chats.append(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔕 Bạn đã tắt nhận cảnh báo từ hệ thống. Các quản trị viên khác vẫn nhận bình thường."
                                }, timeout=5)
                            elif txt in ("/unmute", "/bat_bao_dong", "bat bao dong", "bat_bao_dong"):
                                from app.config import save_settings
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id in muted_chats:
                                    muted_chats.remove(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔔 Bạn đã bật lại nhận cảnh báo từ hệ thống."
                                }, timeout=5)
                            elif txt in ("/mute_buzzer_30", "tat coi 30p", "tắt còi 30p", "tắt còi 30 phút"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = time.time() + 30 * 60
                                SystemStatus.add_log("Telegram Bot: Đã tắt còi báo động vật lý trong 30 phút.", "warning")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔇 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt còi báo động vật lý trong 30 phút thành công!"
                                }, timeout=5)
                            elif txt in ("/mute_buzzer_60", "tat coi 1h", "tắt còi 1h", "tắt còi 1 tiếng", "tắt còi 60 phút"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = time.time() + 60 * 60
                                SystemStatus.add_log("Telegram Bot: Đã tắt còi báo động vật lý trong 1 tiếng.", "warning")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔇 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt còi báo động vật lý trong 1 tiếng thành công!"
                                }, timeout=5)
                            elif txt in ("/unmute_buzzer", "bat coi", "bật còi", "bật còi báo động"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = 0.0
                                SystemStatus.add_log("Telegram Bot: Đã bật lại còi báo động vật lý.", "success")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔊 [ĐIỀU KHIỂN TỪ XA]\nĐã kích hoạt lại còi báo động vật lý thành công!"
                                }, timeout=5)
                            elif txt in ("/test_coi", "/test_còi", "test coi", "test còi"):
                                from app.config import SystemStatus
                                SystemStatus.mock_buzzer = True
                                SystemStatus.add_log("Telegram Bot: Đang kiểm tra còi báo động (3 giây)...", "info")
                                
                                def off_worker():
                                    time.sleep(3.0)
                                    SystemStatus.mock_buzzer = False
                                    SystemStatus.add_log("Telegram Bot: Kết thúc kiểm tra còi báo động.", "success")
                                    
                                threading.Thread(target=off_worker, daemon=True).start()
                                
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔊 [KIỂM TRA PHẦN CỨNG]\nĐang kiểm tra còi báo động kêu trong 3 giây..."
                                }, timeout=5)
                            elif txt in ("/test_den", "/test_đèn", "test den", "test đèn"):
                                from app.processors import set_light_state
                                from app.config import SystemStatus
                                set_light_state(True)
                                SystemStatus.add_log("Telegram Bot: Đang kiểm tra đèn chiếu sáng (5 giây)...", "info")
                                
                                def off_worker_light():
                                    time.sleep(5.0)
                                    set_light_state(False)
                                    SystemStatus.add_log("Telegram Bot: Kết thúc kiểm tra đèn chiếu sáng.", "success")
                                    
                                threading.Thread(target=off_worker_light, daemon=True).start()
                                
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "💡 [KIỂM TRA PHẦN CỨNG]\nĐang kiểm tra đèn chiếu sáng bật trong 5 giây..."
                                }, timeout=5)
                                
                        # Xử lý sự kiện bấm nút inline
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            cb_data = cb["data"]
                            chat_id = str(cb["message"]["chat"]["id"])
                            message_id = cb["message"]["message_id"]
                            
                            response_text = ""
                            new_markup = None
                            
                            # Xác định trạng thái câm hiện tại cho riêng user này
                            muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                            is_muted = chat_id in muted_chats
                            mute_text = "🔔 Bật Lại Báo Động" if is_muted else "🔕 Tắt Báo Động"
                            mute_cb = "unmute_alerts" if is_muted else "mute_alerts"
                            
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

                            if cb_data.startswith("tg_cam_"):
                                cam_id = cb_data.split("tg_cam_")[-1]
                                from app.config import get_cameras_config, save_full_cameras_config, SystemStatus
                                cameras = get_cameras_config()
                                found = False
                                status_str = "Tắt"
                                for cam in cameras:
                                    if cam["camera_id"] == cam_id:
                                        new_state = not cam.get("alerts_enabled", True)
                                        cam["alerts_enabled"] = new_state
                                        found = True
                                        status_str = "Bật" if new_state else "Tắt"
                                        response_text = f"🔄 Đã {status_str} cảnh báo camera '{cam_id}'"
                                        break
                                if found:
                                    save_full_cameras_config(cameras)
                                    SystemStatus.add_log(f"Telegram Bot: Đã {status_str.lower()} cảnh báo cho camera '{cam_id}'", "info")
                                else:
                                    response_text = "Không tìm thấy camera tương ứng."
                                
                                send_camera_menu(token, chat_id, message_id)
                                
                            elif cb_data == "refresh_cam_menu":
                                response_text = "Đã làm mới danh sách camera."
                                send_camera_menu(token, chat_id, message_id)
                                
                            elif cb_data == "mute_alerts":
                                from app.config import save_settings, SystemStatus
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id not in muted_chats:
                                    muted_chats.append(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                SystemStatus.add_log(f"Telegram Bot: Người dùng {chat_id} đã tắt nhận cảnh báo.", "warning")
                                response_text = "🔕 Bạn đã tắt nhận cảnh báo từ hệ thống. Các quản trị viên khác vẫn nhận bình thường."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data == "unmute_alerts":
                                from app.config import save_settings, SystemStatus
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id in muted_chats:
                                    muted_chats.remove(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                SystemStatus.add_log(f"Telegram Bot: Người dùng {chat_id} đã bật lại nhận cảnh báo.", "success")
                                response_text = "🔔 Bạn đã bật lại nhận cảnh báo từ hệ thống."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data.startswith("pause_"):
                                parts = cb_data.split("_")
                                cam_id = "_".join(parts[1:-1])
                                duration = int(parts[-1])
                                
                                from app.processors import pause_camera_alerts
                                pause_camera_alerts(cam_id, duration)
                                response_text = f"⏸️ Đã tạm ngắt cảnh báo camera '{cam_id}' trong {duration} phút."
                                new_markup = get_alert_keyboard(chat_id, camera_id, is_paused=True)
                                
                            elif cb_data.startswith("resume_"):
                                cam_id = cb_data.split("resume_")[-1]
                                
                                from app.processors import resume_camera_alerts
                                resume_camera_alerts(cam_id)
                                response_text = f"▶️ Đã bật lại cảnh báo camera '{cam_id}' thành công."
                                new_markup = get_alert_keyboard(chat_id, camera_id, is_paused=False)
                                
                            elif cb_data == "toggle_light":
                                from app.processors import set_light_state
                                from app.config import SystemStatus
                                new_state = not SystemStatus.light_active
                                set_light_state(new_state)
                                state_str = "BẬT" if new_state else "TẮT"
                                response_text = f"💡 Đã {state_str} đèn thành công."
                                new_markup = get_alert_keyboard(chat_id, camera_id)

                            elif cb_data.startswith("mute_buzzer_"):
                                minutes = int(cb_data.split("_")[-1])
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = time.time() + minutes * 60
                                SystemStatus.add_log(f"Telegram Bot: Đã tắt còi báo động vật lý trong {minutes} phút.", "warning")
                                response_text = f"🔇 Đã tắt còi báo động vật lý trong {minutes} phút."
                                new_markup = get_alert_keyboard(chat_id, camera_id)

                            elif cb_data == "unmute_buzzer":
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = 0.0
                                SystemStatus.add_log("Telegram Bot: Đã kích hoạt lại còi báo động vật lý.", "success")
                                response_text = "🔊 Đã kích hoạt lại còi báo động vật lý."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data == "test_buzzer_3s":
                                from app.config import SystemStatus
                                SystemStatus.mock_buzzer = True
                                SystemStatus.add_log("Telegram Bot: Đang kiểm tra còi báo động (3 giây)...", "info")
                                
                                def off_worker():
                                    time.sleep(3.0)
                                    SystemStatus.mock_buzzer = False
                                    SystemStatus.add_log("Telegram Bot: Kết thúc kiểm tra còi báo động.", "success")
                                    
                                threading.Thread(target=off_worker, daemon=True).start()
                                response_text = "🔊 Đang test còi kêu trong 3 giây..."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data == "test_light_5s":
                                from app.processors import set_light_state
                                from app.config import SystemStatus
                                set_light_state(True)
                                SystemStatus.add_log("Telegram Bot: Đang kiểm tra đèn chiếu sáng (5 giây)...", "info")
                                
                                def off_worker_light():
                                    time.sleep(5.0)
                                    set_light_state(False)
                                    SystemStatus.add_log("Telegram Bot: Kết thúc kiểm tra đèn chiếu sáng.", "success")
                                    
                                threading.Thread(target=off_worker_light, daemon=True).start()
                                response_text = "💡 Đang test bật đèn trong 5 giây..."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
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
