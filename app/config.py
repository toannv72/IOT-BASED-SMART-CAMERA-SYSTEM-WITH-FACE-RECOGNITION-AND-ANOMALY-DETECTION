import os
import json

SETTINGS_FILE = "settings.json"
CONFIG_FILE = "cameras_config.json"
MAPS_FILE = "maps_config.json"

# Cấu hình mặt bằng mặc định
DEFAULT_MAPS = [
    {"map_id": "khu_a_tang_1", "name": "Khu A - Tầng 1", "image_path": "/static/emap_khu_a_tang_1.png"},
    {"map_id": "khu_a_tang_2", "name": "Khu A - Tầng 2", "image_path": "/static/emap_khu_a_tang_2.png"},
    {"map_id": "khu_a_tang_3", "name": "Khu A - Tầng 3", "image_path": "/static/emap_khu_a_tang_3.png"},
    {"map_id": "khu_b_tang_1", "name": "Khu B - Tầng 1", "image_path": "/static/emap_khu_b_tang_1.png"},
    {"map_id": "khu_b_tang_2", "name": "Khu B - Tầng 2", "image_path": "/static/emap_khu_b_tang_2.png"},
]

def get_maps_config():
    if os.path.exists(MAPS_FILE):
        try:
            with open(MAPS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CONFIG] Lỗi tải maps_config.json: {e}")
    # Khởi tạo mặc định nếu file chưa tồn tại
    save_maps_config(DEFAULT_MAPS)
    return DEFAULT_MAPS

def save_maps_config(maps):
    try:
        with open(MAPS_FILE, "w", encoding="utf-8") as f:
            json.dump(maps, f, indent=4, ensure_ascii=False)
        print(f"[CONFIG] Đã lưu cấu hình bản đồ vào {MAPS_FILE}")
    except Exception as e:
        print(f"[CONFIG] Lỗi ghi maps_config.json: {e}")

# Cài đặt mặc định của hệ thống
DEFAULT_SETTINGS = {
    "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "telegram_chats": ["8438973190"],
    "conf_threshold": 0.25,
    "counter_cooldown": 45,
    "telegram_cooldown": 15,
    "alerts_enabled": True,
    "tts_enabled": False,
    "tts_voice": "vi-VN",
    "auto_cleanup_enabled": False,
    "cleanup_max_size_gb": 2.0,
    "cleanup_older_than_days": 7,
    "loitering_threshold": 10,
    "face_log_cooldown": 30,
    "face_threshold": 0.80,
    "fire_conf_threshold": 0.55,
    "fire_frame_buffer": 25,
    "record_full_video": False,
    "house_locked": False,
    "muted_telegram_chats": [],
    "unmutable_alerts": ["fire", "gas"],
    "light_auto_off_seconds": 30,
    "light_trigger_mode": "always",
    "light_schedule_start": "18:00",
    "light_schedule_end": "06:00",
    "light_brightness_threshold": 60
}

# Tải cài đặt lúc khởi chạy
settings = DEFAULT_SETTINGS.copy()

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Đảm bảo không ghi đè các cấu hình thiếu bằng giá trị mặc định
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in loaded:
                        loaded[k] = v
                settings = loaded
        except Exception as e:
            print(f"[CONFIG] Lỗi tải settings.json: {e}. Sử dụng cài đặt mặc định.")
    else:
        save_settings()

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        print(f"[CONFIG] Đã lưu cấu hình mới vào {SETTINGS_FILE}")
    except Exception as e:
        print(f"[CONFIG] Lỗi ghi file cấu hình: {e}")

def get_cameras_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cams = json.load(f)
                # Đảm bảo mỗi camera đều có map_id
                updated = False
                for cam in cams:
                    if "map_id" not in cam:
                        cam["map_id"] = "khu_a_tang_1"
                        updated = True
                if updated:
                    save_full_cameras_config(cams)
                return cams
        except Exception as e:
            print(f"[CONFIG] Lỗi tải cameras_config.json: {e}")
    # Trả về cấu hình mặc định nếu file lỗi hoặc không tồn tại
    return [
        {
            "camera_id": "Cam_Cua_Chinh",
            "source": "video.mp4",
            "features": ["face_id"],
            "line": [[154, 218], [412, 214]],
            "in_direction": "down",
            "roi": [[100, 100], [540, 100], [540, 300], [100, 300]],
            "schedule_enabled": False,
            "schedule_start": "23:00",
            "schedule_end": "06:00",
            "map_x": 23.5,
            "map_y": 38.0,
            "map_id": "khu_a_tang_1"
        },
        {
            "camera_id": "Cam_Cua_Sau",
            "source": "video1.mp4",
            "features": ["intrusion_roi"],
            "line": [[166, 211], [349, 265]],
            "in_direction": "up",
            "roi": [[150, 150], [550, 150], [580, 350], [120, 350]],
            "schedule_enabled": False,
            "schedule_start": "23:00",
            "schedule_end": "06:00",
            "map_x": 88.0,
            "map_y": 74.0,
            "map_id": "khu_a_tang_1"
        },
        {
            "camera_id": "Cam_Hanh_Lang",
            "source": "video.mp4",
            "features": ["fall_detection"],
            "line": [[100, 180], [540, 180]],
            "in_direction": "down",
            "roi": [[100, 100], [540, 100], [540, 300], [100, 300]],
            "schedule_enabled": False,
            "schedule_start": "23:00",
            "schedule_end": "06:00",
            "map_x": 69.5,
            "map_y": 42.0,
            "map_id": "khu_a_tang_1"
        }
    ]

def save_cameras_config(camera_id, p1, p2):
    try:
        cameras = get_cameras_config()
        for cam in cameras:
            if cam["camera_id"] == camera_id:
                cam["line"] = [list(p1), list(p2)]
                break
        save_full_cameras_config(cameras)
        print(f"[CONFIG] Đã lưu vạch kẻ camera {camera_id} mới.")
    except Exception as e:
        print(f"[CONFIG] Lỗi lưu vạch kẻ camera: {e}")

def save_full_cameras_config(cameras):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cameras, f, indent=4, ensure_ascii=False)
        print(f"[CONFIG] Đã lưu toàn bộ cấu hình {len(cameras)} camera vào {CONFIG_FILE}")
    except Exception as e:
        print(f"[CONFIG] Lỗi lưu cấu hình camera: {e}")

# Nạp cấu hình ban đầu
load_settings()

import threading
import time
from datetime import datetime

# Trạng thái hệ thống thời gian thực dùng chung
class SystemStatus:
    intrusion_active = False
    fall_active = False
    fire_active = False
    gas_active = False
    mock_gas_leak = False
    buzzer_active = False
    mock_buzzer = False
    buzzer_mute_until = 0.0  # Thời điểm hết hiệu lực tắt còi tạm thời (timestamp)
    light_active = False
    new_logs = []
    log_lock = threading.Lock()
    
    # Hỗ trợ bàn giao người nhà liên camera (Cross-Camera Whitelist Handover)
    handovers = []  # Danh sách các sự kiện bàn giao: [{"cam_id": str, "name": str, "timestamp": float}]
    handover_lock = threading.Lock()
    
    @classmethod
    def add_log(cls, msg, log_type=""):
        with cls.log_lock:
            cls.new_logs.append({
                "msg": msg,
                "type": log_type,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            if len(cls.new_logs) > 50:
                cls.new_logs.pop(0)

    @classmethod
    def add_handover(cls, cam_id, name, timestamp):
        with cls.handover_lock:
            # Dọn dẹp các sự kiện cũ quá 10 giây
            cls.handovers = [h for h in cls.handovers if timestamp - h["timestamp"] <= 10.0]
            cls.handovers.append({
                "cam_id": cam_id,
                "name": name,
                "timestamp": timestamp
            })
            print(f"[CROSS-CAM] Đăng ký sự kiện bàn giao người nhà '{name}' từ camera '{cam_id}'")

    @classmethod
    def find_matching_handover(cls, current_cam_id, current_time):
        with cls.handover_lock:
            # Dọn dẹp các sự kiện cũ quá 10 giây
            cls.handovers = [h for h in cls.handovers if current_time - h["timestamp"] <= 10.0]
            # Tìm sự kiện bàn giao gần nhất từ camera khác
            for h in sorted(cls.handovers, key=lambda x: x["timestamp"], reverse=True):
                if h["cam_id"] != current_cam_id:
                    cls.handovers.remove(h)
                    return h["name"]
            return None

