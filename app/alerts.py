import os
import cv2
import time
import json
import requests
import threading
from datetime import datetime, timedelta
from app.config import settings, SystemStatus
from app.database import SessionLocal, SystemEventLog
from app.telemetry import TelemetryTracker

# Quản lý thời gian gửi cảnh báo trước đó để tính Cooldown tránh gửi lặp
last_alert_times = {}
incident_trackers = {}  # cooldown_key -> {"first_time": float, "last_alert_time": float, "alert_count": int}
alert_lock = threading.Lock()

def reset_alert_incident(alert_type, camera_id=None, face_name=None):
    """
    Giải tỏa sự cố cảnh báo ngay lập tức (De-escalation):
    Xóa trạng thái incident và cooldown để khi hết bất thường hoặc nhận diện được người nhà thì ngừng spam,
    đồng thời nếu sau này có sự cố mới thật sự thì cảnh báo đầu tiên sẽ được gửi ngay lập tức (0 giây trễ).
    """
    with alert_lock:
        if camera_id is None:
            keys_to_del = [k for k in list(incident_trackers.keys()) if k.startswith(f"{alert_type}_")]
            for k in keys_to_del:
                incident_trackers.pop(k, None)
                last_alert_times.pop(k, None)
        else:
            cooldown_key = f"{alert_type}_{camera_id}"
            if face_name:
                cooldown_key = f"{alert_type}_{camera_id}_{face_name}"
            incident_trackers.pop(cooldown_key, None)
            last_alert_times.pop(cooldown_key, None)

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
    
    # Dòng 1: Mở khóa cửa Solenoid từ xa (3 giây)
    keyboard.append([{"text": "🔓 Mở Khóa Cửa (3s)", "callback_data": "unlock_door"}])

    # Dòng 2: Điều khiển tắt còi vật lý tạm thời
    is_buzzer_muted = time.time() < getattr(SystemStatus, "buzzer_mute_until", 0.0)
    if is_buzzer_muted:
        keyboard.append([{"text": "🔊 Bật Lại Còi Báo Động", "callback_data": "unmute_buzzer"}])
    else:
        keyboard.append([
            {"text": "🔇 Tắt Còi 30p", "callback_data": "mute_buzzer_30"},
            {"text": "🔇 Tắt Còi 1h", "callback_data": "mute_buzzer_60"}
        ])
        
    # Dòng 3: Tắt nhận thông báo cho user hiện tại & Tạm dừng camera (nếu có)
    row3 = [{"text": mute_text, "callback_data": mute_cb}]
    if camera_id and camera_id != "Unknown":
        if is_paused:
            row3.append({"text": "▶️ Bật Lại Cam", "callback_data": f"resume_{camera_id}"})
        else:
            row3.append({"text": f"⏸️ Tạm Dừng Cam 30m", "callback_data": f"pause_{camera_id}_30"})
    keyboard.append(row3)
    
    # Dòng 4: Bật/Tắt đèn thông minh theo trạng thái thực tế
    light_active = getattr(SystemStatus, "light_active", False)
    light_text = "🔌 Tắt Đèn" if light_active else "💡 Bật Đèn"
    keyboard.append([
        {"text": light_text, "callback_data": "toggle_light"}
    ])
    
    # Dòng 5: Kiểm tra phần cứng (Test còi, Test đèn)
    keyboard.append([
        {"text": "🔊 Test Còi 3s", "callback_data": "test_buzzer_3s"},
        {"text": "💡 Test Đèn 5s", "callback_data": "test_light_5s"}
    ])
    
    # Dòng 6: Quản lý danh sách camera & Trạng thái hệ thống
    keyboard.append([
        {"text": "📹 Danh Sách Camera", "callback_data": "open_cam_menu"},
        {"text": "📊 Trạng Thái Hệ Thống", "callback_data": "system_status_info"}
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
        # Nếu là thông báo nhận diện khuôn mặt người quen (Known Face):
        # Áp dụng thời gian giãn cách (face_log_cooldown) do người dùng tùy chỉnh trong Cài đặt
        if alert_type == "face" and face_name and face_name != "Unknown":
            face_cooldown = max(float(settings.get("face_log_cooldown", 300)), 5.0)
            last_time = last_alert_times.get(cooldown_key, 0)
            if current_time - last_time < face_cooldown:
                return
            last_alert_times[cooldown_key] = current_time
        else:
            # Tự động dọn dẹp các incident đã kết thúc (không có cảnh báo mới trong 120 giây)
            for k in list(incident_trackers.keys()):
                if current_time - incident_trackers[k]["last_alert_time"] > 120.0:
                    incident_trackers.pop(k, None)
                    last_alert_times.pop(k, None)

            incident = incident_trackers.get(cooldown_key)
            if incident is None:
                # Sự cố mới toanh (Xâm nhập / Người lạ): Gửi ngay lập tức (Lần 1 - Không trễ)
                incident_trackers[cooldown_key] = {
                    "first_time": current_time,
                    "last_alert_time": current_time,
                    "alert_count": 1
                }
                last_alert_times[cooldown_key] = current_time
            else:
                # Sự cố đang tiếp diễn kéo dài: Áp dụng Lũy tiến thời gian chờ (Exponential Backoff)
                count = incident["alert_count"]
                time_since_last = current_time - incident["last_alert_time"]
                
                # Cảnh báo cháy nổ hoặc khí ga: Giữ tần suất khẩn cấp 30s
                if alert_type in ["fire", "gas"]:
                    required_interval = max(cooldown, 30.0)
                else:
                    # Cảnh báo xâm nhập / người lạ:
                    # Lần 1: Ngay lập tức
                    # Lần 2: sau 60 giây (nếu đối tượng vẫn chưa rời đi)
                    # Lần 3: sau 300 giây (5 phút)
                    # Lần 4 trở đi: sau 900 giây (15 phút) để triệt tiêu hoàn toàn tình trạng spam rung điện thoại
                    if count == 1:
                        required_interval = max(cooldown, 60.0)
                    elif count == 2:
                        required_interval = 300.0
                    else:
                        required_interval = 900.0
                        
                if time_since_last < required_interval:
                    return
                    
                incident["alert_count"] += 1
                incident["last_alert_time"] = current_time
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
                t_tg_start = time.time()
                requests.post(url, data=payload, files=files, timeout=10)
                t_tg_end = time.time()
                TelemetryTracker.record_telegram_latency(t_tg_end - t_tg_start)
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

                            if txt in ("/unlock", "/mo_cua", "/mở_cửa", "unlock", "mo cua", "mở cửa", "mo_cua"):
                                from app.processors import unlock_door
                                unlock_door(duration=3.0)
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔓 *[ĐIỀU KHIỂN TỪ XA]*\nĐã kích hoạt rơ-le mở khóa cửa điện từ (Solenoid) trong 3 giây thành công!",
                                    "parse_mode": "Markdown",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/status", "/trang_thai", "status", "trang thai", "trạng thái", "kiem tra", "kiểm tra"):
                                from app.config import SystemStatus
                                is_buzzer_muted = time.time() < getattr(SystemStatus, "buzzer_mute_until", 0.0)
                                buzzer_str = "🔇 Đang tắt tạm thời" if is_buzzer_muted else ("🔊 Đang kêu" if SystemStatus.buzzer_active else "🟢 Bình thường")
                                light_str = "💡 Đang BẬT" if getattr(SystemStatus, "light_active", False) else "🔌 Đang TẮT"
                                gas_str = "⚠️ PHÁT HIỆN RÒ RỈ!" if getattr(SystemStatus, "gas_active", False) else "🟢 An toàn"
                                door_str = "🔓 Đang mở" if getattr(SystemStatus, "door_unlock_active", False) else "🔒 Đang khóa"
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                user_alert_str = "🔕 Đang tắt (Không nhận cảnh báo)" if chat_id in muted_chats else "🔔 Đang bật (Đang nhận cảnh báo)"
                                
                                status_msg = (
                                    "📊 *BÁO CÁO TRẠNG THÁI HỆ THỐNG SMART CAMERA*\n\n"
                                    f"• Cảm biến khí ga MQ-2: {gas_str}\n"
                                    f"• Đèn chiếu sáng thông minh: {light_str}\n"
                                    f"• Còi báo động vật lý: {buzzer_str}\n"
                                    f"• Khóa cửa Solenoid: {door_str}\n"
                                    f"• Nhận cảnh báo tài khoản của bạn: {user_alert_str}\n\n"
                                    "👉 Sử dụng bàn phím bên dưới để điều khiển nhanh:"
                                )
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": status_msg,
                                    "parse_mode": "Markdown",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/start", "/help", "/menu", "help", "tro giup", "trợ giúp", "menu", "hi", "hello", "chào", "xin chào"):
                                help_msg = (
                                    "👋 *XIN CHÀO! ĐÂY LÀ HỆ THỐNG SMART CAMERA AN NINH*\n\n"
                                    "Bạn có thể điều khiển hệ thống bằng các nút bên dưới hoặc gửi tin nhắn lệnh:\n"
                                    "• `/unlock` hoặc `mở cửa`: Mở khóa cửa điện từ 3 giây\n"
                                    "• `/cameras` hoặc `cam`: Xem & Bật/Tắt cảnh báo từng camera\n"
                                    "• `/status` hoặc `status`: Báo cáo trạng thái hệ thống\n"
                                    "• `/light_on` hoặc `bật đèn`: Bật đèn chiếu sáng\n"
                                    "• `/light_off` hoặc `tắt đèn`: Tắt đèn chiếu sáng\n"
                                    "• `/mute` hoặc `tắt báo động`: Tắt nhận cảnh báo riêng cho tài khoản\n"
                                    "• `/unmute` hoặc `bật báo động`: Bật lại nhận cảnh báo\n"
                                    "• `/test_coi`: Thử còi kêu trong 3 giây\n"
                                    "• `/test_den`: Thử bật đèn trong 5 giây"
                                )
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": help_msg,
                                    "parse_mode": "Markdown",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/light_on", "bat den", "bật đèn", "bật đèn chiếu sáng"):
                                from app.processors import set_light_state
                                set_light_state(True)
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "💡 [ĐIỀU KHIỂN TỪ XA]\nĐã bật đèn chiếu sáng thông minh thành công.",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/light_off", "tat den", "tắt đèn", "tắt đèn chiếu sáng"):
                                from app.processors import set_light_state
                                set_light_state(False)
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔌 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt đèn chiếu sáng thông minh thành công.",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/cameras", "/cam", "/danh_sach_cam", "cameras", "cam"):
                                send_camera_menu(token, chat_id)

                            elif txt in ("/mute", "/tat_bao_dong", "tat bao dong", "tat_bao_dong", "tắt báo động"):
                                from app.config import save_settings
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id not in muted_chats:
                                    muted_chats.append(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔕 Bạn đã tắt nhận cảnh báo từ hệ thống. Các quản trị viên khác vẫn nhận bình thường.\n👉 Để bật lại bất cứ lúc nào, gõ `/unmute` hoặc bấm nút bên dưới.",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/unmute", "/bat_bao_dong", "bat bao dong", "bat_bao_dong", "bật báo động"):
                                from app.config import save_settings
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id in muted_chats:
                                    muted_chats.remove(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔔 Bạn đã bật lại nhận cảnh báo từ hệ thống thành công.",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/mute_buzzer_30", "tat coi 30p", "tắt còi 30p", "tắt còi 30 phút"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = time.time() + 30 * 60
                                SystemStatus.add_log("Telegram Bot: Đã tắt còi báo động vật lý trong 30 phút.", "warning")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔇 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt còi báo động vật lý trong 30 phút thành công!",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/mute_buzzer_60", "tat coi 1h", "tắt còi 1h", "tắt còi 1 tiếng", "tắt còi 60 phút"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = time.time() + 60 * 60
                                SystemStatus.add_log("Telegram Bot: Đã tắt còi báo động vật lý trong 1 tiếng.", "warning")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔇 [ĐIỀU KHIỂN TỪ XA]\nĐã tắt còi báo động vật lý trong 1 tiếng thành công!",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)

                            elif txt in ("/unmute_buzzer", "bat coi", "bật còi", "bật còi báo động"):
                                from app.config import SystemStatus
                                SystemStatus.buzzer_mute_until = 0.0
                                SystemStatus.add_log("Telegram Bot: Đã bật lại còi báo động vật lý.", "success")
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": "🔊 [ĐIỀU KHIỂN TỪ XA]\nĐã kích hoạt lại còi báo động vật lý thành công!",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
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
                                    "text": "🔊 [KIỂM TRA PHẦN CỨNG]\nĐang kiểm tra còi báo động kêu trong 3 giây...",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
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
                                    "text": "💡 [KIỂM TRA PHẦN CỨNG]\nĐang kiểm tra đèn chiếu sáng bật trong 5 giây...",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)
                            else:
                                # Fallback: Tin nhắn không khớp lệnh -> Gửi menu phản hồi ngay lập tức, không để bot im lặng
                                fallback_msg = (
                                    f"🤖 Hệ thống nhận được tin nhắn: *{txt}*\n\n"
                                    "Bạn có thể sử dụng bảng điều khiển bên dưới hoặc gõ `/help` để xem danh sách câu lệnh."
                                )
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    "chat_id": chat_id,
                                    "text": fallback_msg,
                                    "parse_mode": "Markdown",
                                    "reply_markup": json.dumps(get_alert_keyboard(chat_id))
                                }, timeout=5)
                                
                        # Xử lý sự kiện bấm nút inline
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            cb_data = cb.get("data", "")
                            cb_msg = cb.get("message", {})
                            chat_id = str(cb_msg.get("chat", {}).get("id", ""))
                            message_id = cb_msg.get("message_id")
                            
                            response_text = ""
                            new_markup = None
                            
                            # Xác định trạng thái câm hiện tại cho riêng user này
                            muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                            is_muted = chat_id in muted_chats
                            
                            # Trích xuất camera_id từ markup hiện tại nếu có
                            camera_id = None
                            try:
                                markup = cb_msg.get("reply_markup", {})
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
                                
                                try:
                                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", 
                                                  json={"callback_query_id": cb_id, "text": response_text}, timeout=5)
                                except Exception:
                                    pass
                                send_camera_menu(token, chat_id, message_id)
                                continue
                                
                            elif cb_data == "refresh_cam_menu":
                                response_text = "Đã làm mới danh sách camera."
                                try:
                                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", 
                                                  json={"callback_query_id": cb_id, "text": response_text}, timeout=5)
                                except Exception:
                                    pass
                                send_camera_menu(token, chat_id, message_id)
                                continue

                            elif cb_data == "open_cam_menu":
                                response_text = "Đang mở danh sách camera..."
                                try:
                                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", 
                                                  json={"callback_query_id": cb_id, "text": response_text}, timeout=5)
                                except Exception:
                                    pass
                                send_camera_menu(token, chat_id)
                                continue

                            elif cb_data == "system_status_info":
                                from app.config import SystemStatus
                                is_buzzer_muted = time.time() < getattr(SystemStatus, "buzzer_mute_until", 0.0)
                                buzzer_str = "🔇 Đang tắt" if is_buzzer_muted else ("🔊 Đang kêu" if SystemStatus.buzzer_active else "🟢 Tắt")
                                light_str = "💡 BẬT" if getattr(SystemStatus, "light_active", False) else "🔌 TẮT"
                                gas_str = "⚠️ RÒ RỈ!" if getattr(SystemStatus, "gas_active", False) else "🟢 An toàn"
                                door_str = "🔓 Mở" if getattr(SystemStatus, "door_unlock_active", False) else "🔒 Đóng"
                                response_text = f"Gas: {gas_str} | Đèn: {light_str} | Còi: {buzzer_str} | Cửa: {door_str}"
                                new_markup = get_alert_keyboard(chat_id, camera_id)

                            elif cb_data == "unlock_door":
                                from app.processors import unlock_door
                                unlock_door(duration=3.0)
                                response_text = "🔓 Đã mở khóa cửa điện từ (Solenoid) trong 3 giây!"
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data == "mute_alerts":
                                from app.config import save_settings, SystemStatus
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id not in muted_chats:
                                    muted_chats.append(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                SystemStatus.add_log(f"Telegram Bot: Người dùng {chat_id} đã tắt nhận cảnh báo.", "warning")
                                response_text = "🔕 Đã tắt nhận cảnh báo từ bot. Bấm 'Bật Lại Báo Động' để mở lại."
                                new_markup = get_alert_keyboard(chat_id, camera_id)
                                
                            elif cb_data == "unmute_alerts":
                                from app.config import save_settings, SystemStatus
                                muted_chats = [str(x) for x in settings.get("muted_telegram_chats", [])]
                                if chat_id in muted_chats:
                                    muted_chats.remove(chat_id)
                                    settings["muted_telegram_chats"] = muted_chats
                                    save_settings()
                                SystemStatus.add_log(f"Telegram Bot: Người dùng {chat_id} đã bật lại nhận cảnh báo.", "success")
                                response_text = "🔔 Đã bật lại nhận cảnh báo thành công."
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
                                new_state = not getattr(SystemStatus, "light_active", False)
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

                            # Phản hồi toast thông báo nhanh tới Telegram
                            try:
                                answer_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                                requests.post(answer_url, json={"callback_query_id": cb_id, "text": response_text}, timeout=5)
                            except Exception as err:
                                print(f"[TELEGRAM] Lỗi answerCallbackQuery: {err}")
                            
                            # Cập nhật tin nhắn (phân biệt tin nhắn có ảnh và tin nhắn văn bản thường)
                            try:
                                has_photo = ("photo" in cb_msg) or ("caption" in cb_msg)
                                if has_photo:
                                    edit_url = f"https://api.telegram.org/bot{token}/editMessageCaption"
                                    original_caption = cb_msg.get("caption", "") or ""
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
                                    edit_url = f"https://api.telegram.org/bot{token}/editMessageText"
                                    original_text = cb_msg.get("text", "") or ""
                                    if "\n\n👉 [Hệ Thống]" in original_text:
                                        original_text = original_text.split("\n\n👉 [Hệ Thống]")[0]
                                    edit_payload = {
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "text": original_text + f"\n\n👉 [Hệ Thống] {response_text}"
                                    }
                                    if new_markup:
                                        edit_payload["reply_markup"] = json.dumps(new_markup)
                                    requests.post(edit_url, json=edit_payload, timeout=5)
                            except Exception as err:
                                print(f"[TELEGRAM] Lỗi cập nhật nội dung tin nhắn sau callback: {err}")
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
