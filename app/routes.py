import os
import io
import json
import time
import hashlib
import secrets
import numpy as np
import psutil
import torch
from fastapi import Request, Response, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from PIL import Image

from app import app
import app.config as config
from app.config import SystemStatus
from app.database import SessionLocal, User, FaceRecord, SystemEventLog
from app.processors import camera_fps, gen_face_stream, gen_roi_stream, gen_counter_stream, gen_fall_stream

# =========================================================================
# MẬT KHẨU MÃ HÓA BẰNG PBKDF2 HASH (Không phụ thuộc thư viện ngoài bcrypt)
# =========================================================================
def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    hash_val = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}:{hash_val}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hash_val = stored_hash.split(':')
        calc_val = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(hash_val, calc_val)
    except Exception:
        return False

# =========================================================================
# GIAO DIỆN GLASSMORPHISM ĐĂNG NHẬP VÀ ĐĂNG KÝ (TỰ CHỨA - ĐẸP MẮT)
# =========================================================================
def get_auth_html(mode="login", error="", success=""):
    title = "Đăng Nhập Hệ Thống" if mode == "login" else "Đăng Ký Tài Khoản"
    button_text = "Đăng Nhập" if mode == "login" else "Đăng Ký"
    switch_link = "/register" if mode == "login" else "/login"
    switch_text = "Chưa có tài khoản? Đăng ký ngay" if mode == "login" else "Đã có tài khoản? Đăng nhập"
    
    error_html = f'<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> {error}</div>' if error else ""
    success_html = f'<div class="alert alert-success"><i class="fas fa-check-circle"></i> {success}</div>' if success else ""
    
    return f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - AI Surveillance</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{
                --bg-color: #0b0f19;
                --panel-bg: rgba(17, 24, 39, 0.7);
                --border-color: rgba(255, 255, 255, 0.08);
                --primary: #3b82f6;
                --primary-glow: rgba(59, 130, 246, 0.5);
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            /* Hiệu ứng nền */
            .bg-glow {{
                position: absolute;
                width: 400px;
                height: 400px;
                background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 1;
                pointer-events: none;
            }}
            .card {{
                width: 400px;
                background: var(--panel-bg);
                backdrop-filter: blur(16px);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 40px;
                z-index: 2;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                text-align: center;
            }}
            h2 {{ font-weight: 600; margin-bottom: 24px; letter-spacing: -0.5px; }}
            .input-group {{
                position: relative;
                margin-bottom: 20px;
                text-align: left;
            }}
            .input-group label {{
                display: block;
                font-size: 13px;
                color: var(--text-muted);
                margin-bottom: 6px;
            }}
            .input-group i {{
                position: absolute;
                bottom: 12px;
                left: 14px;
                color: var(--text-muted);
            }}
            .input-group input {{
                width: 100%;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 10px 10px 10px 38px;
                color: #fff;
                font-family: inherit;
                outline: none;
                transition: 0.3s;
            }}
            .input-group input:focus {{
                border-color: var(--primary);
                box-shadow: 0 0 8px var(--primary-glow);
            }}
            .btn {{
                width: 100%;
                background: var(--primary);
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 15px;
                font-weight: 500;
                font-family: inherit;
                cursor: pointer;
                transition: 0.3s;
                margin-top: 10px;
            }}
            .btn:hover {{
                box-shadow: 0 0 15px var(--primary);
                transform: translateY(-1px);
            }}
            .alert {{
                padding: 10px;
                border-radius: 8px;
                font-size: 13px;
                margin-bottom: 20px;
                text-align: left;
            }}
            .alert-danger {{ background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; }}
            .alert-success {{ background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(16, 185, 129, 0.4); color: #a7f3d0; }}
            .switch-link {{
                display: block;
                margin-top: 20px;
                font-size: 13px;
                color: var(--primary);
                text-decoration: none;
                transition: 0.2s;
            }}
            .switch-link:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="bg-glow"></div>
        <div class="card">
            <h2>{title}</h2>
            {error_html}
            {success_html}
            <form action="" method="post">
                <div class="input-group">
                    <label for="username">Tên tài khoản</label>
                    <i class="fas fa-user"></i>
                    <input type="text" id="username" name="username" placeholder="Nhập username..." required>
                </div>
                <div class="input-group">
                    <label for="password">Mật khẩu</label>
                    <i class="fas fa-lock"></i>
                    <input type="password" id="password" name="password" placeholder="Nhập password..." required>
                </div>
                <button type="submit" class="btn">{button_text}</button>
            </form>
            <a href="{switch_link}" class="switch-link">{switch_text}</a>
        </div>
    </body>
    </html>
    """

# =========================================================================
# ROUTING ĐĂNG NHẬP & ĐĂNG KÝ (AUTHENTICATION ENDPOINTS)
# =========================================================================
@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    # Nếu đã đăng nhập thì tự chuyển sang Dashboard chính
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return HTMLResponse(get_auth_html(mode="login"))

@app.post("/login", response_class=HTMLResponse)
def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(get_auth_html(mode="login", error="Sai tài khoản hoặc mật khẩu!"))
        
    # Tạo phiên đăng nhập (Lưu ID vào session cookie đã được mã hóa ký tên)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    print(f"[AUTH] Người dùng '{username}' đăng nhập thành công.")
    return RedirectResponse(url="/", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return HTMLResponse(get_auth_html(mode="register"))

@app.post("/register", response_class=HTMLResponse)
def post_register(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == username).first()
    
    if existing_user:
        db.close()
        return HTMLResponse(get_auth_html(mode="register", error="Tài khoản này đã tồn tại trên hệ thống!"))
        
    # Đăng ký tài khoản mới và băm mật khẩu
    new_user = User(username=username, password_hash=hash_password(password))
    try:
        db.add(new_user)
        db.commit()
        db.close()
        print(f"[AUTH] Đã đăng ký thành công tài khoản mới: {username}")
        return HTMLResponse(get_auth_html(mode="login", success="Đăng ký thành công! Hãy đăng nhập."))
    except Exception as e:
        db.rollback()
        db.close()
        return HTMLResponse(get_auth_html(mode="register", error=f"Lỗi đăng ký tài khoản: {e}"))

@app.get("/logout")
def get_logout(request: Request):
    # Xóa toàn bộ dữ liệu session của cookie
    request.session.clear()
    print("[AUTH] Người dùng đã đăng xuất.")
    return RedirectResponse(url="/login")

# =========================================================================
# ROUTING DASHBOARD VÀ STREAM (PROTECTED ROUTES)
# =========================================================================
@app.get("/")
def read_root(request: Request):
    # Route Guard: Bảo vệ trang chính
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
        
    html_path = os.path.join("templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Thư mục templates hoặc tệp index.html không tồn tại!</h1>")

@app.get("/gpu_info")
def get_gpu_info(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    return {
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_active": torch.cuda.is_available()
    }

@app.get("/system_status")
def get_system_status(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    with SystemStatus.log_lock:
        logs_to_return = list(SystemStatus.new_logs)
        SystemStatus.new_logs.clear()  # Xóa để tránh hiển thị lặp
        
    return {
        "intrusion_alert": SystemStatus.intrusion_active,
        "fall_alert": SystemStatus.fall_active,
        "new_logs": logs_to_return
    }

@app.get("/settings")
def get_settings_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    return config.settings

@app.post("/settings")
async def update_settings_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    payload = await request.json()
    for k, v in payload.items():
        if k in config.DEFAULT_SETTINGS:
            # Chuyển đổi kiểu dữ liệu phù hợp
            if k == "conf_threshold":
                config.settings[k] = float(v)
            elif k in ["counter_cooldown", "telegram_cooldown"]:
                config.settings[k] = int(v)
            elif k == "alerts_enabled":
                config.settings[k] = bool(v)
            else:
                config.settings[k] = v
                
    config.save_settings()
    SystemStatus.add_log("Cấu hình hệ thống đã được cập nhật trực tiếp.", "success")
    return {"message": "Đã cập nhật cài đặt!"}

# =========================================================================
# LUỒNG LIVE STREAM VIDEO FEED (PROTECTED FEED ROUTES)
# =========================================================================
# =========================================================================
# LUỒNG LIVE STREAM VIDEO FEED (DỮ LIỆU ĐỘNG & TƯƠNG THÍCH NGƯỢC)
# =========================================================================
@app.get("/video_feed/{camera_id}")
def video_feed_dynamic(camera_id: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    from app.processors import gen_dynamic_stream
    return StreamingResponse(gen_dynamic_stream(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/face")
def video_feed_face(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    from app.processors import gen_dynamic_stream
    return StreamingResponse(gen_dynamic_stream("Cam_Cua_Chinh"), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/roi")
def video_feed_roi(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    from app.processors import gen_dynamic_stream
    return StreamingResponse(gen_dynamic_stream("Cam_Cua_Sau"), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/counter")
def video_feed_counter(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    from app.processors import gen_dynamic_stream
    return StreamingResponse(gen_dynamic_stream("Cam_Cua_Chinh"), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_feed/fall")
def video_feed_fall(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    from app.processors import gen_dynamic_stream
    return StreamingResponse(gen_dynamic_stream("Cam_Hanh_Lang"), media_type="multipart/x-mixed-replace; boundary=frame")

# =========================================================================
# ENDPOINTS FACE DATABASE (FACE REGISTRATION & LISTS)
# =========================================================================
@app.post("/register_face")
async def register_face(request: Request, name: str = Form(...), file: UploadFile = File(...)):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    image_bytes = await file.read()
    
    # Sử dụng import lười để tránh circular import khi tải mô hình AI
    from app.ai import mtcnn_single, resnet, device
    
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    face = mtcnn_single(img)
    if face is None:
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt nào trong ảnh!")
        
    face = face.unsqueeze(0).to(device)
    embedding = resnet(face).detach().cpu().numpy()[0]
    
    emb_list = embedding.tolist()
    emb_json = json.dumps(emb_list)
    
    db = SessionLocal()
    new_face = FaceRecord(name=name, embedding=emb_json)
    db.add(new_face)
    db.commit()
    db.refresh(new_face)
    db.close()
    
    SystemStatus.add_log(f"Đăng ký khuôn mặt thành công: {name}", "success")
    return {"message": "Đăng ký thành công!", "id": new_face.id, "name": new_face.name}

@app.get("/faces")
def get_all_faces(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    return [{"id": f.id, "name": f.name} for f in faces]

@app.delete("/faces/{face_id}")
def delete_face(face_id: int, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    db = SessionLocal()
    face = db.query(FaceRecord).filter(FaceRecord.id == face_id).first()
    if not face:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy khuôn mặt này.")
    
    name = face.name
    db.delete(face)
    db.commit()
    db.close()
    
    SystemStatus.add_log(f"Đã xóa khuôn mặt: {name} (ID: {face_id})", "danger")
    return {"message": "Đã xóa thành công!"}

# =========================================================================
# API TÍNH NĂNG NÂNG CAO ĐỒ ÁN (HEALTH & LOGS ARCHIVE)
# =========================================================================
@app.get("/api/system_health")
def get_system_health(request: Request):
    """
    Trả về dữ liệu hiệu năng phần cứng hệ thống và FPS hiện tại của từng camera.
    """
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
        
    # Tài nguyên CPU & RAM
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    
    # Tài nguyên GPU & VRAM
    gpu_active = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_active else "CPU"
    
    # Lấy dung lượng bộ nhớ VRAM đang sử dụng
    if gpu_active:
        gpu_allocated = torch.cuda.memory_allocated(0) / (1024 ** 2)  # MB
        gpu_cached = torch.cuda.memory_reserved(0) / (1024 ** 2)      # MB
        # Ước lượng % tải GPU (sử dụng random mock từ 20-40% nếu không gọi được nvidia-smi)
        gpu_percent = 25.0
        try:
            import subprocess
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                encoding="utf-8"
            )
            gpu_percent = float(result.strip())
        except Exception:
            pass
    else:
        gpu_allocated = 0.0
        gpu_cached = 0.0
        gpu_percent = 0.0

    return {
        "cpu_usage": cpu_percent,
        "ram_usage": ram_percent,
        "gpu_active": gpu_active,
        "gpu_name": gpu_name,
        "gpu_usage": gpu_percent,
        "vram_allocated_mb": round(gpu_allocated, 1),
        "vram_reserved_mb": round(gpu_cached, 1),
        "fps": camera_fps
    }

@app.get("/api/logs")
def get_system_logs(request: Request):
    """
    Trả về lịch sử toàn bộ sự kiện cảnh báo được lưu trữ trong SQLite.
    """
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
        
    db = SessionLocal()
    try:
        # Lấy 100 sự kiện mới nhất
        logs = db.query(SystemEventLog).order_by(SystemEventLog.id.desc()).limit(100).all()
        return [
            {
                "id": log.id,
                "event_type": log.event_type,
                "message": log.message,
                "camera_id": log.camera_id,
                "image_path": log.image_path,
                "timestamp": log.timestamp
            } for log in logs
        ]
    except Exception as e:
        print(f"[ROUTES] [ERROR] Lỗi truy xuất cơ sở dữ liệu: {e}")
        return []
    finally:
        db.close()

@app.get("/api/capture_frame/{camera_id}")
def capture_camera_frame(camera_id: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
        
    from app.processors import camera_states
    state = camera_states.get(camera_id)
    if state is None or getattr(state, "last_frame", None) is None:
        raise HTTPException(status_code=400, detail="Camera chưa hoạt động hoặc chưa có khung hình nào!")
        
    import cv2
    ret, buffer = cv2.imencode('.jpg', state.last_frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Không thể mã hóa khung hình!")
        
    return Response(content=buffer.tobytes(), media_type="image/jpeg")

# =========================================================================
# API QUẢN LÝ TÀI KHOẢN (USER MANAGEMENT ENDPOINTS)
# =========================================================================
@app.get("/api/users")
def get_users(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return [{"id": u.id, "username": u.username} for u in users]

@app.post("/api/users")
def create_user(request: Request, username: str = Form(...), password: str = Form(...)):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Tài khoản này đã tồn tại!")
    new_user = User(username=username, password_hash=hash_password(password))
    try:
        db.add(new_user)
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã tạo tài khoản quản trị mới: {username}", "success")
        return {"message": "Đã tạo tài khoản quản trị thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    payload = await request.json()
    password = payload.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Mật khẩu không được để trống!")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng này!")
    user.password_hash = hash_password(password)
    try:
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã đổi mật khẩu thành công cho user ID: {user_id}", "info")
        return {"message": "Đã đổi mật khẩu thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, request: Request):
    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="Bạn không thể tự xóa tài khoản của chính mình!")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng!")
    username = user.username
    try:
        db.delete(user)
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã xóa tài khoản: {username}", "danger")
        return {"message": "Đã xóa tài khoản thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================================
# API CẤU HÌNH CAMERA ĐỘNG (CAMERA CONFIGURATION ENDPOINTS)
# =========================================================================
@app.get("/api/cameras")
def get_cameras(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    return config.get_cameras_config()

@app.post("/api/cameras")
async def add_camera(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    new_cam = await request.json()
    camera_id = new_cam.get("camera_id")
    if not camera_id:
        raise HTTPException(status_code=400, detail="Thiếu Camera ID!")
    
    cameras = config.get_cameras_config()
    if any(c["camera_id"] == camera_id for c in cameras):
        raise HTTPException(status_code=400, detail="Camera ID này đã tồn tại!")
    
    # Thiết lập giá trị mặc định cho camera mới
    if "source" not in new_cam: new_cam["source"] = "video.mp4"
    if "features" not in new_cam: new_cam["features"] = ["people_counter"]
    if "line" not in new_cam: new_cam["line"] = [[100, 180], [540, 180]]
    if "in_direction" not in new_cam: new_cam["in_direction"] = "down"
    if "roi" not in new_cam: new_cam["roi"] = [[100, 100], [540, 100], [540, 300], [100, 300]]
    if "schedule_enabled" not in new_cam: new_cam["schedule_enabled"] = False
    if "schedule_start" not in new_cam: new_cam["schedule_start"] = "23:00"
    if "schedule_end" not in new_cam: new_cam["schedule_end"] = "06:00"

    cameras.append(new_cam)
    config.save_full_cameras_config(cameras)
    SystemStatus.add_log(f"Đã thêm camera mới: {camera_id}", "success")
    return {"message": "Đã thêm camera thành công!"}

@app.put("/api/cameras/{camera_id}")
async def update_camera(camera_id: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    updated_cam = await request.json()
    cameras = config.get_cameras_config()
    found_idx = -1
    for idx, cam in enumerate(cameras):
        if cam["camera_id"] == camera_id:
            found_idx = idx
            break
    if found_idx == -1:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera!")
    
    # Cập nhật thông số
    cameras[found_idx].update(updated_cam)
    config.save_full_cameras_config(cameras)
    SystemStatus.add_log(f"Đã cập nhật camera: {camera_id}", "info")
    return {"message": "Đã cập nhật camera thành công!"}

@app.delete("/api/cameras/{camera_id}")
def delete_camera(camera_id: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    cameras = config.get_cameras_config()
    filtered_cameras = [c for c in cameras if c["camera_id"] != camera_id]
    if len(filtered_cameras) == len(cameras):
        raise HTTPException(status_code=404, detail="Không tìm thấy camera!")
    config.save_full_cameras_config(filtered_cameras)
    SystemStatus.add_log(f"Đã xóa camera: {camera_id}", "danger")
    return {"message": "Đã xóa camera thành công!"}
