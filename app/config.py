import os
import json
import copy
import threading

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
    "face_log_cooldown": 300,
    "face_threshold": 0.80,
    "fire_conf_threshold": 0.55,
    "fire_frame_buffer": 25,
    "fall_conf_threshold": 0.25,
    "fall_frame_buffer": 6,
    "fall_smart_posture": True,
    "record_full_video": False,
    "house_locked": False,
    "muted_telegram_chats": [],
    "unmutable_alerts": ["fire", "gas"],
    "light_auto_off_seconds": 30,
    "light_trigger_mode": "always",
    "light_schedule_start": "18:00",
    "light_schedule_end": "06:00",
    "light_brightness_threshold": 60,
    "gdrive_enabled": False,
    "gdrive_webhook_url": "",
    "gdrive_folder_id": "",
    "gdrive_retention_days": 30,
    "gdrive_auto_cleanup": True,
    "gdrive_sync_alerts": True,
    "gdrive_sync_recordings": False,
    "gdrive_sync_db": True,
    "gdrive_organize_by_date": True,
    "gdrive_target_mode": "auto_folder",
    "gdrive_folder_name": "SmartCamera_Cloud_Backup",
    "gdrive_backup_links": [],
    "gdrive_min_free_mb": 100,
    "local_storage_path": "",
    "local_backup_storage_path": "",
    "local_min_free_gb": 1.0,
    "remote_access_auto_start": False
}

# Tải cài đặt lúc khởi chạy
settings = DEFAULT_SETTINGS.copy()
_last_active_local_tier = "primary"

def _check_dir_writable_and_space(path_str: str, min_free_gb: float = 0.0) -> tuple:
    """
    Kiểm tra xem thư mục có thể tạo/ghi được không và còn đủ dung lượng trống (>= min_free_gb) hay không.
    Trả về (ok: bool, free_gb: float, reason: str)
    """
    try:
        import shutil
        os.makedirs(path_str, exist_ok=True)
        total, used, free = shutil.disk_usage(os.path.abspath(path_str))
        free_gb = free / (1024 ** 3)
        if min_free_gb > 0 and free_gb < min_free_gb:
            return False, round(free_gb, 2), f"Dung lượng trống ({free_gb:.2f} GB) thấp hơn ngưỡng an toàn ({min_free_gb:.2f} GB)"
        return True, round(free_gb, 2), "OK"
    except Exception as e:
        return False, 0.0, str(e)

def get_storage_base_dir() -> str:
    """
    Trả về đường dẫn thư mục gốc dùng để lưu trữ cục bộ theo chuỗi dự phòng (Failover):
    1. Ưu tiên Ổ đĩa chính (`local_storage_path`, hoặc `static` nếu để trống).
    2. Nếu Ổ đĩa chính bị đầy (còn trống < `local_min_free_gb`) hoặc lỗi ghi, tự động chuyển sang
       Ổ đĩa dự phòng (`local_backup_storage_path`).
    3. Nếu cả hai đều lỗi, fallback an toàn về `static`.
    """
    global _last_active_local_tier
    primary_raw = str(settings.get("local_storage_path", "") or "").strip()
    backup_raw = str(settings.get("local_backup_storage_path", "") or "").strip()
    min_free_gb = float(settings.get("local_min_free_gb", 1.0) or 0.0)

    primary_target = primary_raw if primary_raw else "static"
    # Nếu chưa cấu hình ổ dự phòng thì không chặn ngưỡng min_free_gb ở ổ chính để vẫn cố ghi được tới khi đầy thật
    effective_min_gb = min_free_gb if backup_raw else 0.05

    ok_pri, free_pri, reason_pri = _check_dir_writable_and_space(primary_target, effective_min_gb)
    if ok_pri:
        _last_active_local_tier = "primary"
        return primary_target

    # Nếu ổ chính không đủ dung lượng hoặc lỗi -> Chuyển tiếp sang Ổ cứng dự phòng (Backup Disk)
    if backup_raw:
        ok_bak, free_bak, reason_bak = _check_dir_writable_and_space(backup_raw, 0.05)
        if ok_bak:
            if _last_active_local_tier != "backup":
                _last_active_local_tier = "backup"
                print(f"[STORAGE FAILOVER] ⚠️ Ổ lưu trữ chính '{primary_target}' không đủ chỗ ({reason_pri}). Đã tự động chuyển sang Ổ cứng dự phòng: '{backup_raw}' (Trống {free_bak} GB)!")
            return backup_raw

    # Fallback cuối cùng
    os.makedirs("static", exist_ok=True)
    return "static"

def get_all_candidate_storage_dirs(subfolder: str) -> list:
    """
    Trả về danh sách tất cả các thư mục có thể chứa tệp (Cả ổ chính, ổ dự phòng và static)
    để phục vụ việc đọc/phát lại video hoặc xem ảnh không bị mất dấu khi chuyển ổ.
    """
    dirs = []
    for base in [
        get_storage_base_dir(),
        str(settings.get("local_storage_path", "") or "").strip(),
        str(settings.get("local_backup_storage_path", "") or "").strip(),
        "static"
    ]:
        if not base:
            continue
        d = os.path.join(base, subfolder)
        abs_d = os.path.abspath(d)
        if abs_d not in [os.path.abspath(x) for x in dirs]:
            dirs.append(d)
    return dirs

def get_alerts_storage_dir() -> str:
    base = get_storage_base_dir()
    d = os.path.join(base, "alerts")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.path.join("static", "alerts")
        os.makedirs(d, exist_ok=True)
    return d

def get_recordings_storage_dir() -> str:
    base = get_storage_base_dir()
    d = os.path.join(base, "recordings")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.path.join("static", "recordings")
        os.makedirs(d, exist_ok=True)
    return d

def get_media_web_path(subfolder: str, filename: str) -> str:
    """
    Trả về đường dẫn URL để trình duyệt tải ảnh/video.
    Nếu đang lưu ở thư mục mặc định 'static' thì trả về '/static/<subfolder>/<filename>',
    nếu lưu ở ổ đĩa chính hoặc ổ đĩa dự phòng khác thì trả về '/api/storage/<subfolder>/<filename>'.
    """
    active_base = get_storage_base_dir()
    if os.path.abspath(active_base) != os.path.abspath("static"):
        return f"/api/storage/{subfolder}/{filename}"
    return f"/static/{subfolder}/{filename}"

def resolve_web_path_to_local(web_path: str) -> str:
    """
    Chuyển đổi đường dẫn web ('/static/alerts/...' hoặc '/api/storage/alerts/...')
    thành đường dẫn tệp vật lý thực tế trên ổ cứng (tự động tìm trên cả ổ chính, ổ dự phòng và static).
    """
    if not web_path:
        return ""
    clean = web_path.lstrip("/")
    subfolder = None
    fname = None
    if clean.startswith("api/storage/"):
        parts = clean.split("/")
        if len(parts) >= 4:
            subfolder = parts[2]
            fname = "/".join(parts[3:])
    elif clean.startswith("static/alerts/"):
        subfolder = "alerts"
        fname = clean.split("static/alerts/", 1)[1]
    elif clean.startswith("static/recordings/"):
        subfolder = "recordings"
        fname = clean.split("static/recordings/", 1)[1]

    if subfolder and fname:
        for cand_dir in get_all_candidate_storage_dirs(subfolder):
            p = os.path.join(cand_dir, fname)
            if os.path.exists(p):
                return p
        return os.path.join("static", subfolder, fname)
    return clean

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

# Bộ nhớ đệm cấu hình camera theo thời điểm sửa file, tránh đọc/parse JSON trên mỗi khung hình
_cameras_cache = None
_cameras_mtime = None
_cameras_lock = threading.Lock()

def get_cameras_config():
    global _cameras_cache, _cameras_mtime
    if os.path.exists(CONFIG_FILE):
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            with _cameras_lock:
                if _cameras_cache is not None and _cameras_mtime == mtime:
                    return copy.deepcopy(_cameras_cache)
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cams = json.load(f)
                # Đảm bảo mỗi camera đều có map_id, recording_mode và gdrive_sync
                updated = False
                for cam in cams:
                    if "map_id" not in cam:
                        cam["map_id"] = "khu_a_tang_1"
                        updated = True
                    if "recording_mode" not in cam:
                        cam["recording_mode"] = "alerts_only"
                        updated = True
                    if "gdrive_sync" not in cam:
                        cam["gdrive_sync"] = True
                        updated = True
                if updated:
                    save_full_cameras_config(cams)
                    return copy.deepcopy(cams)
            with _cameras_lock:
                # Không ghi đè nếu một lần lưu mới hơn vừa cập nhật bộ nhớ đệm
                if _cameras_mtime is None or mtime >= _cameras_mtime:
                    _cameras_cache = cams
                    _cameras_mtime = mtime
            return copy.deepcopy(cams)
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
    global _cameras_cache, _cameras_mtime
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cameras, f, indent=4, ensure_ascii=False)
        with _cameras_lock:
            _cameras_cache = copy.deepcopy(cameras)
            _cameras_mtime = os.path.getmtime(CONFIG_FILE)
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
    startup_active = False
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

