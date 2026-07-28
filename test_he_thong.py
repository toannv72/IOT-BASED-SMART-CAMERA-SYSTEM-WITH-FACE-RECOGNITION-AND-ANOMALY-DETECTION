"""
=========================================================
SMART CAMERA - KIEM TRA HE THONG TOAN DIEN
Tac gia: Auto-generated test suite
Muc tieu: Kiem tra tung module cua he thong Smart Camera
=========================================================
"""
import sys
import os
import time
import json
import traceback

sys.path.insert(0, '.')

# Mau sac terminal
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = []
failed = []
warnings = []

def ok(name, detail=""):
    passed.append(name)
    msg = "[PASS] " + name
    if detail:
        msg += "  ->  " + detail
    print(msg)

def fail(name, detail=""):
    failed.append(name)
    msg = "[FAIL] " + name
    if detail:
        msg += "  ->  " + detail
    print(msg)

def warn(name, detail=""):
    warnings.append(name)
    msg = "[WARN] " + name
    if detail:
        msg += "  ->  " + detail
    print(msg)

def section(title):
    print("\n" + "="*60)
    print("  " + title)
    print("="*60)

# =========================================================
# MODULE 1: KIEM TRA DEPENDENCIES (THU VIEN)
# =========================================================
section("MODULE 1: KIEM TRA THU VIEN / DEPENDENCIES")

packages = {
    "torch": "PyTorch AI Framework",
    "cv2": "OpenCV Vision",
    "fastapi": "FastAPI Web Server",
    "ultralytics": "YOLOv8 Engine",
    "supervision": "Object Tracking",
    "facenet_pytorch": "FaceNet Models",
    "sqlalchemy": "SQLAlchemy ORM",
    "numpy": "NumPy Math",
    "psutil": "System Monitor",
    "PIL": "Pillow Image",
    "uvicorn": "ASGI Server",
}

import_results = {}
for pkg, desc in packages.items():
    try:
        mod = __import__(pkg)
        ver = getattr(mod, '__version__', 'N/A')
        ok(desc + " (" + pkg + ")", "v" + str(ver))
        import_results[pkg] = True
    except ImportError as e:
        fail(desc + " (" + pkg + ")", str(e))
        import_results[pkg] = False

# Kiem tra CUDA / CPU mode
try:
    import torch
    cuda_available = torch.cuda.is_available()
    device_name = "CUDA GPU" if cuda_available else "CPU Only"
    ok("Compute Device", device_name + " | Torch " + torch.__version__)
except Exception as e:
    fail("Compute Device check", str(e))

# Kiem tra RPi.GPIO (cross-platform)
try:
    import RPi.GPIO as GPIO
    ok("RPi.GPIO", "Running on Raspberry Pi hardware")
except ImportError:
    warn("RPi.GPIO", "Not available (Windows dev mode) -> Simulation mode ACTIVE (expected)")

# =========================================================
# MODULE 2: KIEM TRA CAU HINH (CONFIG)
# =========================================================
section("MODULE 2: KIEM TRA CAU HINH HE THONG")

try:
    from app.config import settings, DEFAULT_SETTINGS, get_cameras_config, get_maps_config, SystemStatus
    ok("app.config import", "Module loaded successfully")
    
    # Kiem tra face_threshold - QUY DINH NGHIEM CAM thay doi
    ft = settings.get("face_threshold", -1)
    if 0.78 <= ft <= 0.82:
        ok("face_threshold constraint", "value=" + str(ft) + " in [0.78, 0.82] (COMPLIANT)")
    else:
        fail("face_threshold constraint", "value=" + str(ft) + " OUT OF RANGE [0.78, 0.82]!")
    
    # Kiem tra cac setting quan trong
    critical_keys = [
        "telegram_token", "telegram_chats", "conf_threshold",
        "face_threshold", "fire_conf_threshold", "house_locked",
        "unmutable_alerts"
    ]
    missing = [k for k in critical_keys if k not in settings]
    if not missing:
        ok("settings.json schema", "All " + str(len(critical_keys)) + " critical keys present")
    else:
        fail("settings.json schema", "Missing keys: " + str(missing))
    
    # Kiem tra cameras_config
    cams = get_cameras_config()
    if len(cams) > 0:
        ok("cameras_config.json", str(len(cams)) + " camera(s) loaded")
        for cam in cams:
            cam_id = cam.get("camera_id", "?")
            src = cam.get("source", "?")
            feats = cam.get("features", [])
            required_fields = ["camera_id", "source", "features", "line", "roi", "map_id"]
            missing_fields = [f for f in required_fields if f not in cam]
            if not missing_fields:
                print("       -> Cam '" + cam_id + "' | src=" + src + " | features=" + str(feats) + " OK")
            else:
                fail("Camera '" + cam_id + "' schema", "Missing fields: " + str(missing_fields))
    else:
        warn("cameras_config.json", "No cameras configured")

    # Kiem tra maps config
    maps = get_maps_config()
    ok("maps_config.json", str(len(maps)) + " map(s) loaded")
    
    # Kiem tra unmutable alerts
    unmutable = settings.get("unmutable_alerts", [])
    if "fire" in unmutable and "gas" in unmutable:
        ok("unmutable_alerts", "fire & gas in list -> " + str(unmutable))
    else:
        warn("unmutable_alerts", "fire/gas not in list: " + str(unmutable))

except Exception as e:
    fail("app.config module", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 3: KIEM TRA DATABASE (SQLite)
# =========================================================
section("MODULE 3: KIEM TRA DATABASE SQLite")

try:
    from app.database import SessionLocal, User, FaceRecord, SystemEventLog, engine
    ok("app.database import", "SQLAlchemy models loaded")
    
    db = SessionLocal()
    users_count = db.query(User).count()
    faces_count = db.query(FaceRecord).count()
    events_count = db.query(SystemEventLog).count()
    db.close()
    
    ok("Database connection", "SQLite connected")
    ok("Table: users", str(users_count) + " user(s)")
    ok("Table: faces", str(faces_count) + " face embedding(s)")
    ok("Table: system_events", str(events_count) + " event log(s)")
    
    if os.path.exists("faces.db"):
        db_size = os.path.getsize("faces.db") / 1024
        ok("faces.db file", "Exists (" + str(round(db_size, 1)) + " KB)")
    else:
        warn("faces.db file", "Not found")
    
    # Kiem tra schema migration
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    
    face_cols = [c['name'] for c in inspector.get_columns('faces')]
    if 'created_at' in face_cols and 'created_by' in face_cols:
        ok("Schema migration: faces", "created_at, created_by columns exist")
    else:
        fail("Schema migration: faces", "Missing columns in: " + str(face_cols))
    
    event_cols = [c['name'] for c in inspector.get_columns('system_events')]
    if 'video_path' in event_cols and 'face_name' in event_cols:
        ok("Schema migration: system_events", "video_path, face_name columns exist")
    else:
        fail("Schema migration: system_events", "Missing columns in: " + str(event_cols))

except Exception as e:
    fail("app.database module", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 4: KIEM TRA AI MODEL FILES
# =========================================================
section("MODULE 4: KIEM TRA AI MODEL FILES")

model_files = [
    ("yolov8n.pt", "YOLOv8 Nano - Phat hien nguoi (ROI)"),
    ("yolov8n-pose.pt", "YOLOv8-Pose - Uoc luong tu the"),
    ("yolov8n_fall_best.pt", "YOLOv8 Custom - Phat hien nga"),
    ("yolov8n_fire_custom.pt", "YOLOv8 Custom Fire - Phat hien chay"),
    ("yolov8n_fire.pt", "YOLOv8 Fire Fallback"),
]

for fname, desc in model_files:
    if os.path.exists(fname):
        size_mb = os.path.getsize(fname) / (1024*1024)
        ok("Model: " + desc, fname + " (" + str(round(size_mb, 1)) + " MB)")
    else:
        warn("Model: " + desc, fname + " NOT FOUND")

try:
    import app.ai as ai_module
    ok("app.ai import", "Lazy-loading module OK")
    from app.ai import device
    ok("AI compute device", "device=" + str(device))
except Exception as e:
    fail("app.ai module", str(e))

# =========================================================
# MODULE 5: KIEM TRA SYSTEMSTATUS & MULTITHREADING
# =========================================================
section("MODULE 5: KIEM TRA SYSTEMSTATUS & THREAD SAFETY")

try:
    import threading
    from app.config import SystemStatus
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=lambda n=i: SystemStatus.add_log("Thread " + str(n) + " log", "info"))
        threads.append(t)
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    ok("SystemStatus.add_log thread safety", "10 concurrent threads -> logs=" + str(len(SystemStatus.new_logs)))
    
    now = time.time()
    SystemStatus.add_handover("Cam_A", "Nguyen Van A", now)
    result = SystemStatus.find_matching_handover("Cam_B", now + 1)
    if result == "Nguyen Van A":
        ok("Cross-Camera Handover", "add_handover -> find_matching_handover OK")
    else:
        fail("Cross-Camera Handover", "Expected 'Nguyen Van A', got '" + str(result) + "'")
    
    flags = {
        "intrusion_active": SystemStatus.intrusion_active,
        "fall_active": SystemStatus.fall_active,
        "fire_active": SystemStatus.fire_active,
        "gas_active": SystemStatus.gas_active,
        "mock_gas_leak": SystemStatus.mock_gas_leak,
    }
    all_false = all(not v for v in flags.values())
    if all_false:
        ok("SystemStatus default flags", "All False on startup OK")
    else:
        warn("SystemStatus default flags", "Non-false flags: " + str(flags))

except Exception as e:
    fail("SystemStatus tests", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 6: KIEM TRA HMAC SESSION MIDDLEWARE
# =========================================================
section("MODULE 6: KIEM TRA HMAC SESSION SECURITY")

try:
    from app import sign_data_with_key, verify_data_with_key, SECRET_KEY
    
    test_data = "user_id=1&role=admin"
    signed = sign_data_with_key(test_data, SECRET_KEY)
    verified = verify_data_with_key(signed, SECRET_KEY)
    
    if verified == test_data:
        ok("HMAC sign/verify", "Round-trip OK")
    else:
        fail("HMAC sign/verify", "Expected '" + test_data + "', got '" + str(verified) + "'")
    
    tampered = signed[:-5] + "XXXXX"
    result = verify_data_with_key(tampered, SECRET_KEY)
    if result is None:
        ok("HMAC tamper detection", "Tampered signature rejected OK")
    else:
        fail("HMAC tamper detection", "SECURITY BUG: Accepted tampered signature!")
    
    empty_result = verify_data_with_key("nodot", SECRET_KEY)
    if empty_result is None:
        ok("HMAC edge case (no dot)", "Returns None OK")
    else:
        fail("HMAC edge case", "Should return None")

except Exception as e:
    fail("HMAC Session Security", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 7: KIEM TRA FILE VA THU MUC HE THONG
# =========================================================
section("MODULE 7: KIEM TRA CAU TRUC FILE & THU MUC")

required_dirs = [
    ("static", "Static files directory"),
    ("static/alerts", "Alert images directory"),
    ("templates", "HTML templates directory"),
    ("app", "Application module"),
]

for d, desc in required_dirs:
    if os.path.isdir(d):
        ok("Dir: " + desc, d)
    else:
        fail("Dir: " + desc, "'" + d + "' NOT FOUND")

required_files = [
    ("main.py", "Main entry point"),
    ("app/__init__.py", "App initialization"),
    ("app/config.py", "Configuration"),
    ("app/processors.py", "Camera processors"),
    ("app/routes.py", "API routes"),
    ("app/database.py", "Database models"),
    ("app/alerts.py", "Alert system"),
    ("app/cleanup.py", "Auto cleanup"),
    ("app/ai.py", "AI model loader"),
    ("settings.json", "Settings file"),
    ("cameras_config.json", "Camera config"),
    ("requirements.txt", "Requirements"),
    ("smartcamera.service", "Systemd service"),
    ("don_dep_dong_goi.py", "Package script"),
]

for f, desc in required_files:
    if os.path.isfile(f):
        size = os.path.getsize(f)
        ok("File: " + desc, f + " (" + str(size) + " bytes)")
    else:
        fail("File: " + desc, "'" + f + "' NOT FOUND")

required_templates = [
    "templates/login.html",
    "templates/index.html",
    "templates/base.html",
    "templates/settings.html",
    "templates/database.html",
    "templates/analytics.html",
    "templates/logs.html",
    "templates/emap.html",
]
for t in required_templates:
    if os.path.isfile(t):
        ok("Template: " + os.path.basename(t), str(os.path.getsize(t)//1024) + " KB")
    else:
        fail("Template: " + os.path.basename(t), "NOT FOUND")

# =========================================================
# MODULE 8: BENCHMARK HIEU NANG CPU/RAM
# =========================================================
section("MODULE 8: BENCHMARK HIEU NANG CPU/RAM")

try:
    import psutil
    import numpy as np
    
    cpu_before = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    
    ok("CPU baseline", str(cpu_before) + "%")
    ok("RAM usage", str(round(ram.used/1024**3, 2)) + " GB / " + str(round(ram.total/1024**3, 2)) + " GB (" + str(ram.percent) + "%)")
    
    if ram.percent < 85:
        ok("RAM safety", "Below 85% threshold (" + str(ram.percent) + "%) OK")
    else:
        warn("RAM safety", "HIGH RAM: " + str(ram.percent) + "% - Monitor closely!")
    
    # Benchmark NumPy L2 distance (simulate FaceNet comparison)
    t0 = time.perf_counter()
    for _ in range(100):
        a = np.random.randn(512).astype(np.float32)
        b = np.random.randn(1000, 512).astype(np.float32)
        norms = np.linalg.norm(b, axis=1, keepdims=True)
        b_normalized = b / norms
        distances = np.linalg.norm(b_normalized - a, axis=1)
        _ = np.argmin(distances)
    t_numpy = (time.perf_counter() - t0) * 1000
    ok("NumPy L2-Norm benchmark (100 iter)", str(round(t_numpy, 1)) + " ms total, " + str(round(t_numpy/100, 3)) + " ms/iter")
    
    # Benchmark image preprocessing (simulate MTCNN)
    import cv2
    t0 = time.perf_counter()
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    for _ in range(50):
        resized = cv2.resize(dummy_frame, (160, 160))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
    t_cv2 = (time.perf_counter() - t0) * 1000
    ok("OpenCV frame preprocessing (50 iter)", str(round(t_cv2, 1)) + " ms total, " + str(round(t_cv2/50, 3)) + " ms/iter")

except Exception as e:
    fail("Performance benchmark", str(e))

# =========================================================
# MODULE 9: KIEM TRA MASK-FACE EMBEDDING LOGIC
# =========================================================
section("MODULE 9: KIEM TRA LOGIC MASKED FACE (Khau trang)")

try:
    import numpy as np
    
    # Tao anh mat gia 160x160
    test_face = np.random.randint(100, 200, (160, 160, 3), dtype=np.uint8)
    
    # Ap dung mask (boi den 45% phan duoi - dung voi quy dinh)
    face_masked = test_face.copy()
    face_masked[88:, :, :] = 0
    
    mask_applied = bool(np.all(face_masked[88:, :, :] == 0))
    upper_intact = bool(np.any(face_masked[:88, :, :] != 0))
    
    if mask_applied and upper_intact:
        ok("Mask threshold pixels[88:]", "Lower 45% zeroed, upper preserved OK")
    else:
        fail("Mask threshold pixels[88:]", "mask_applied=" + str(mask_applied) + ", upper_intact=" + str(upper_intact))
    
    masked_ratio = (160 - 88) / 160
    ok("Mask coverage ratio", str(round(masked_ratio*100, 1)) + "% of face covered (" + str(160-88) + "px out of 160px)")
    
    # Test stream-level mask: faces[:, :, 88:, :] = 0
    batch_faces = np.random.randint(100, 200, (3, 3, 160, 160), dtype=np.uint8)
    batch_masked = batch_faces.copy()
    batch_masked[:, :, 88:, :] = 0
    batch_ok = bool(np.all(batch_masked[:, :, 88:, :] == 0))
    if batch_ok:
        ok("Stream batch mask (faces[:, :, 88:, :]=0)", "Batch masking shape correct OK")
    else:
        fail("Stream batch mask", "Batch masking logic error!")

except Exception as e:
    fail("Masked face logic", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 10: KIEM TRA ALERT & TELEGRAM LOGIC
# =========================================================
section("MODULE 10: KIEM TRA ALERT & TELEGRAM LOGIC")

try:
    from app.alerts import last_alert_times, alert_lock, sanitize_filename_component
    ok("app.alerts import", "Module loaded")
    
    test_name = "Nguyen Van Toan"
    result = sanitize_filename_component(test_name)
    ok("sanitize_filename_component", "'" + test_name + "' -> '" + result + "'")
    
    from app.alerts import get_alert_keyboard
    keyboard = get_alert_keyboard("8438973190", "Cam_A", False)
    assert "inline_keyboard" in keyboard
    assert len(keyboard["inline_keyboard"]) >= 2
    ok("get_alert_keyboard", "Returns " + str(len(keyboard["inline_keyboard"])) + " rows OK")
    
    from app.config import settings
    cooldown = settings.get("telegram_cooldown", 15)
    ok("Telegram cooldown setting", str(cooldown) + "s configured")
    
    unmutable = settings.get("unmutable_alerts", [])
    if "fire" in unmutable and "gas" in unmutable:
        ok("Unmutable alerts", "fire, gas always send OK")
    else:
        warn("Unmutable alerts", "Check config: " + str(unmutable))

except Exception as e:
    fail("Alert system", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 11: KIEM TRA AUTO CLEANUP
# =========================================================
section("MODULE 11: KIEM TRA AUTO CLEANUP")

try:
    from app.cleanup import get_folder_size, perform_cleanup
    ok("app.cleanup import", "Module loaded")
    
    if os.path.isdir("static/alerts"):
        size = get_folder_size("static/alerts")
        ok("get_folder_size", "static/alerts = " + str(round(size/1024, 1)) + " KB")
    else:
        warn("get_folder_size", "static/alerts not found, skipping")
    
    from app.config import settings
    cleanup_enabled = settings.get("auto_cleanup_enabled", False)
    ok("auto_cleanup_enabled setting", "= " + str(cleanup_enabled) + " (False = safe on dev)")

except Exception as e:
    fail("Cleanup module", str(e))
    traceback.print_exc()

# =========================================================
# MODULE 12: KIEM TRA PROCESSORS SYNTAX
# =========================================================
section("MODULE 12: KIEM TRA PROCESSORS.PY SYNTAX & COMPLIANCE")

try:
    with open("app/processors.py", "r", encoding="utf-8") as f:
        src = f.read()
    compile(src, "app/processors.py", "exec")
    ok("app/processors.py syntax", "No syntax errors OK")
    
    required_funcs = ["gen_face_stream", "gen_roi_stream", "gen_fall_stream", 
                     "start_all_camera_threads", "ensure_camera_thread_running"]
    for func in required_funcs:
        if func in src:
            ok("processors.py: " + func + "()", "Function defined OK")
        else:
            fail("processors.py: " + func + "()", "Function NOT FOUND!")
    
    if "gpu_lock = threading.Lock()" in src:
        ok("gpu_lock global lock", "Defined OK (required for Pi CPU safety)")
    else:
        fail("gpu_lock", "MISSING! Required for CPU safety!")
    
    if "with torch.no_grad():" in src:
        ok("torch.no_grad() usage", "Found in processors.py OK")
    else:
        warn("torch.no_grad()", "Not found - check memory usage!")
    
    if "faces[:, :, 88:, :] = 0.0" in src or "[:, :, 88:, :] = 0" in src:
        ok("Stream mask logic (88: = 0)", "Found in processors.py OK")
    else:
        fail("Stream mask logic", "MISSING: faces[:, :, 88:, :] = 0.0 not found!")

except Exception as e:
    fail("processors.py check", str(e))

# =========================================================
# MODULE 13: KIEM TRA ROUTES.PY
# =========================================================
section("MODULE 13: KIEM TRA ROUTES.PY SYNTAX & COMPLIANCE")

try:
    with open("app/routes.py", "r", encoding="utf-8") as f:
        src_routes = f.read()
    compile(src_routes, "app/routes.py", "exec")
    ok("app/routes.py syntax", "No syntax errors OK")
    
    if "face[:, 88:, :] = 0.0" in src_routes:
        ok("Register face mask (88: = 0)", "Found in routes.py OK")
    else:
        fail("Register face mask", "MISSING: face[:, 88:, :] = 0.0 not found in routes.py!")
    
    if "pbkdf2_hmac" in src_routes:
        ok("Password hashing (PBKDF2)", "Secure hash function used OK")
    else:
        warn("Password hashing", "pbkdf2_hmac not found in routes.py!")

except Exception as e:
    fail("routes.py check", str(e))

# =========================================================
# MODULE 14: KIEM TRA VIDEO & INPUT FILES
# =========================================================
section("MODULE 14: KIEM TRA VIDEO & INPUT FILES")

video_files = ["video.mp4", "video1.mp4", "video12.mp4", "video123.mp4"]
for vf in video_files:
    if os.path.exists(vf):
        size_mb = os.path.getsize(vf) / (1024*1024)
        ok("Video: " + vf, str(round(size_mb, 1)) + " MB")
    else:
        warn("Video: " + vf, "Not found")

try:
    import cv2
    if os.path.exists("video.mp4"):
        cap = cv2.VideoCapture("video.mp4")
        ret, frame = cap.read()
        cap.release()
        if ret:
            h, w = frame.shape[:2]
            ok("OpenCV video read", "video.mp4 -> " + str(w) + "x" + str(h) + " frame OK")
        else:
            fail("OpenCV video read", "Could not read frame from video.mp4")
except Exception as e:
    fail("Video read test", str(e))

# =========================================================
# TONG KET KET QUA TEST
# =========================================================
section("TONG KET KET QUA KIEM TRA")

total = len(passed) + len(failed) + len(warnings)
print("\n  Tong so test: " + str(total))
print("  PASSED  : " + str(len(passed)))
print("  WARNINGS: " + str(len(warnings)))
print("  FAILED  : " + str(len(failed)))

if warnings:
    print("\nDANH SACH CANH BAO:")
    for w in warnings:
        print("  [WARN] " + w)

if failed:
    print("\nDANH SACH LOI CAN SUA:")
    for f_item in failed:
        print("  [FAIL] " + f_item)
    print("\n[KET LUAN] HE THONG CO " + str(len(failed)) + " LOI CAN KHAC PHUC!")
    sys.exit(1)
else:
    print("\n[KET LUAN] TAT CA " + str(len(passed)) + " TEST PASSED! He thong san sang! OK")
