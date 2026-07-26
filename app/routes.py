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
from fastapi.templating import Jinja2Templates
from PIL import Image

templates = Jinja2Templates(directory="templates")

from app import app
import app.config as config
from app.config import SystemStatus
from app.database import SessionLocal, User, FaceRecord, SystemEventLog
from app.processors import camera_fps, gen_face_stream, gen_roi_stream, gen_fall_stream, ensure_camera_thread_running, stop_camera_thread

# Helper kiểm tra phân quyền quản trị (RBAC)
def check_admin(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    if request.session.get("role") == "operator":
        raise HTTPException(status_code=403, detail="Tài khoản Operator không có quyền thực hiện thao tác này!")

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
# =========================================================================
# ROUTING ĐĂNG NHẬP & ĐĂNG KÝ (AUTHENTICATION ENDPOINTS)
# =========================================================================
@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    # Nếu đã đăng nhập thì tự chuyển sang Dashboard chính
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "login.html", {"error": "", "success": ""})

@app.post("/login", response_class=HTMLResponse)
def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {"error": "Sai tài khoản hoặc mật khẩu!", "success": ""})
        
    # Tạo phiên đăng nhập (Lưu ID và vai trò vào session cookie đã được mã hóa ký tên)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role or "admin"
    print(f"[AUTH] Người dùng '{username}' đăng nhập thành công với vai trò '{user.role or 'admin'}'.")
    return RedirectResponse(url="/", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "register.html", {"error": "", "success": ""})

@app.post("/register", response_class=HTMLResponse)
def post_register(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == username).first()
    
    if existing_user:
        db.close()
        return templates.TemplateResponse(request, "register.html", {"error": "Tài khoản này đã tồn tại trên hệ thống!", "success": ""})
        
    # Đăng ký tài khoản mới và băm mật khẩu, mặc định là admin nếu là tài khoản đăng ký công khai
    new_user = User(username=username, password_hash=hash_password(password), role="admin")
    try:
        db.add(new_user)
        db.commit()
        db.close()
        print(f"[AUTH] Đã đăng ký thành công tài khoản mới: {username}")
        return templates.TemplateResponse(request, "login.html", {"success": "Đăng ký thành công! Hãy đăng nhập.", "error": ""})
    except Exception as e:
        db.rollback()
        db.close()
        return templates.TemplateResponse(request, "register.html", {"error": f"Lỗi đăng ký tài khoản: {e}", "success": ""})

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
    return templates.TemplateResponse(request, "monitor.html", {"active_page": "monitor"})

@app.get("/database", response_class=HTMLResponse)
def get_database_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "database.html", {"active_page": "database"})

@app.get("/logs", response_class=HTMLResponse)
def get_logs_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "logs.html", {"active_page": "logs"})

@app.get("/settings", response_class=HTMLResponse)
def get_settings_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "settings.html", {"active_page": "settings"})

@app.get("/users", response_class=HTMLResponse)
def get_users_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "users.html", {"active_page": "users"})

@app.get("/regulations", response_class=HTMLResponse)
def get_regulations_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "regulations.html", {"active_page": "regulations"})

@app.get("/emap", response_class=HTMLResponse)
def get_emap_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "emap.html", {"active_page": "emap"})

@app.get("/analytics", response_class=HTMLResponse)
def get_analytics_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "analytics.html", {"active_page": "analytics"})

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
        "fire_alert": SystemStatus.fire_active,
        "gas_alert": SystemStatus.gas_active,
        "buzzer_alert": SystemStatus.buzzer_active,
        "house_locked": config.settings.get("house_locked", False),
        "light_active": SystemStatus.light_active,
        "new_logs": logs_to_return
    }

# API JSON Cấu hình hệ thống (Settings endpoints)
@app.get("/api/settings")
def get_settings_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    return config.settings

@app.post("/api/settings")
async def update_settings_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    check_admin(request)
    payload = await request.json()
    for k, v in payload.items():
        if k in config.DEFAULT_SETTINGS:
            # Chuyển đổi kiểu dữ liệu phù hợp
            if k in ["conf_threshold", "fire_conf_threshold", "face_threshold"]:
                config.settings[k] = float(v)
            elif k in ["counter_cooldown", "telegram_cooldown", "cleanup_older_than_days", "loitering_threshold", "face_log_cooldown", "fire_frame_buffer", "light_auto_off_seconds", "light_brightness_threshold"]:
                config.settings[k] = int(v)
            elif k in ["alerts_enabled", "tts_enabled", "auto_cleanup_enabled", "record_full_video"]:
                config.settings[k] = bool(v)
            elif k == "cleanup_max_size_gb":
                config.settings[k] = float(v)
            else:
                config.settings[k] = v
                
    config.save_settings()
    SystemStatus.add_log("Cấu hình hệ thống đã được cập nhật trực tiếp.", "success")
    return {"message": "Đã cập nhật cài đặt!"}

@app.post("/api/settings/test_telegram")
async def test_telegram_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    check_admin(request)
    
    token = config.settings.get("telegram_token")
    chats = config.settings.get("telegram_chats", [])
    
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN" or token.strip() == "":
        raise HTTPException(status_code=400, detail="Vui lòng thay đổi Token mặc định thành Token thực tế của bạn!")
        
    if not chats:
        raise HTTPException(status_code=400, detail="Vui lòng thêm ít nhất một Chat ID hợp lệ!")
        
    import cv2
    # Tạo một ảnh màu đen giả lập camera để gửi test
    test_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(test_frame, "TEST TELEGRAM OK", (120, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.circle(test_frame, (320, 180), 120, (59, 130, 246), 2)
    
    from app.alerts import send_telegram_alert, last_alert_times
    
    # Xóa cooldown của camera test nếu có để gửi được luôn
    cooldown_key = "intrusion_Cam_Test"
    if cooldown_key in last_alert_times:
        del last_alert_times[cooldown_key]
        
    time_str = time.strftime("%H:%M:%S")
    message = f"🔔 [HỆ THỐNG TEST] Kiểm tra kết nối Telegram Bot thành công lúc {time_str}!"
    
    send_telegram_alert(message, test_frame, alert_type="intrusion", camera_id="Cam_Test")
    return {"message": "Đã gửi yêu cầu test đến Telegram Bot. Vui lòng kiểm tra chat Telegram!"}

# API Quy định an ninh hệ thống
@app.get("/api/regulations")
def get_regulations_api(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    file_path = "quy_dinh.txt"
    content = ""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Lỗi đọc file quy định: {e}"
    else:
        content = "Không tìm thấy nội dung quy định. Hãy soạn thảo nội quy mới."
    return {"content": content}

@app.post("/api/regulations")
async def update_regulations_api(request: Request):
    check_admin(request)
    payload = await request.json()
    content = payload.get("content", "")
    file_path = "quy_dinh.txt"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        SystemStatus.add_log("Quy định hệ thống đã được cập nhật bởi quản trị viên.", "info")
        return {"message": "Đã cập nhật quy định thành công!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể ghi file quy định: {e}")

# API Tải ảnh mặt bằng E-map tùy chỉnh
@app.post("/api/emap/upload")
async def upload_emap_background(request: Request, file: UploadFile = File(...)):
    check_admin(request)
    try:
        file_bytes = await file.read()
        os.makedirs("static", exist_ok=True)
        custom_path = os.path.join("static", "emap_custom.png")
        with open(custom_path, "wb") as f:
            f.write(file_bytes)
        SystemStatus.add_log("Đã tải lên ảnh mặt bằng E-map tùy chỉnh mới.", "success")
        return {"message": "Tải ảnh mặt bằng thành công!", "path": "/static/emap_custom.png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu ảnh mặt bằng: {e}")

# =========================================================================
# API QUẢN LÝ BẢN ĐỒ / MẶT BẰNG (MAPS & FLOORS MANAGEMENT ENDPOINTS)
# =========================================================================
@app.get("/api/maps")
def get_maps_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    return config.get_maps_config()

@app.post("/api/maps")
async def add_map_route(request: Request):
    check_admin(request)
    payload = await request.json()
    name = payload.get("name")
    if not name or name.strip() == "":
        raise HTTPException(status_code=400, detail="Tên mặt bằng không được để trống!")
    
    # Vietnamese character mapping to ASCII
    co_dau = "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
    khong_dau = "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    char_map = str.maketrans(co_dau, khong_dau)
    name_ascii = name.lower().translate(char_map)
    import re
    map_id = re.sub(r'[^a-z0-9_]', '_', name_ascii)
    map_id = re.sub(r'_+', '_', map_id).strip('_')
    
    if not map_id:
        raise HTTPException(status_code=400, detail="Tên mặt bằng không hợp lệ!")
        
    maps = config.get_maps_config()
    if any(m["map_id"] == map_id for m in maps):
        raise HTTPException(status_code=400, detail="Mặt bằng này đã tồn tại!")
        
    new_map = {
        "map_id": map_id,
        "name": name.strip(),
        "image_path": f"/static/emap_{map_id}.png"
    }
    maps.append(new_map)
    config.save_maps_config(maps)
    SystemStatus.add_log(f"Đã thêm mặt bằng mới: {name}", "success")
    return {"message": "Đã thêm mặt bằng thành công!", "map": new_map}

@app.delete("/api/maps/{map_id}")
def delete_map_route(map_id: str, request: Request):
    check_admin(request)
    # Kiểm tra xem có camera nào đang sử dụng map_id này không
    cameras = config.get_cameras_config()
    used_cams = [c["camera_id"] for c in cameras if c.get("map_id") == map_id]
    if used_cams:
        raise HTTPException(
            status_code=400, 
            detail=f"Không thể xóa mặt bằng này vì đang có camera đang gán ({', '.join(used_cams)})!"
        )
        
    maps = config.get_maps_config()
    filtered_maps = [m for m in maps if m["map_id"] != map_id]
    if len(filtered_maps) == len(maps):
        raise HTTPException(status_code=404, detail="Không tìm thấy mặt bằng cần xóa!")
        
    config.save_maps_config(filtered_maps)
    
    # Xóa ảnh nền liên quan nếu có
    custom_path = os.path.join("static", f"emap_{map_id}.png")
    if os.path.exists(custom_path):
        try:
            os.remove(custom_path)
        except Exception:
            pass
            
    SystemStatus.add_log(f"Đã xóa mặt bằng: {map_id}", "danger")
    return {"message": "Đã xóa mặt bằng thành công!"}

@app.put("/api/maps/{map_id}")
async def update_map_route(map_id: str, request: Request):
    check_admin(request)
    payload = await request.json()
    new_name = payload.get("name")
    if not new_name or new_name.strip() == "":
        raise HTTPException(status_code=400, detail="Tên mặt bằng không được để trống!")
        
    maps = config.get_maps_config()
    found = False
    for m in maps:
        if m["map_id"] == map_id:
            m["name"] = new_name.strip()
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Không tìm thấy mặt bằng!")
        
    config.save_maps_config(maps)
    SystemStatus.add_log(f"Đã cập nhật tên mặt bằng '{map_id}' thành '{new_name}'", "info")
    return {"message": "Đã cập nhật tên mặt bằng thành công!"}

@app.post("/api/emap/upload/{map_id}")
async def upload_emap_map_background(map_id: str, request: Request, file: UploadFile = File(...)):
    check_admin(request)
    try:
        file_bytes = await file.read()
        os.makedirs("static", exist_ok=True)
        custom_path = os.path.join("static", f"emap_{map_id}.png")
        with open(custom_path, "wb") as f:
            f.write(file_bytes)
        SystemStatus.add_log(f"Đã tải lên ảnh mặt bằng mới cho bản đồ '{map_id}'.", "success")
        return {"message": "Tải ảnh mặt bằng thành công!", "path": f"/static/emap_{map_id}.png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu ảnh mặt bằng: {e}")

# API Dữ liệu phân tích thống kê (Analytics API)
@app.get("/api/analytics")
def get_analytics_api(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    db = SessionLocal()
    try:
        from sqlalchemy import func
        from app.database import SystemEventLog
        
        # 1. Thống kê tổng số lượng theo loại cảnh báo
        counts_by_type = db.query(SystemEventLog.event_type, func.count(SystemEventLog.id)).group_by(SystemEventLog.event_type).all()
        type_summary = {t[0]: t[1] for t in counts_by_type}
        
        # 2. Thống kê số lượng cảnh báo theo ngày (7 ngày gần nhất)
        daily_counts = db.query(
            func.substr(SystemEventLog.timestamp, 1, 10).label("day"),
            SystemEventLog.event_type,
            func.count(SystemEventLog.id)
        ).filter(SystemEventLog.timestamp != None).group_by("day", SystemEventLog.event_type).order_by("day").all()
        
        daily_data = {}
        for row in daily_counts:
            day = row[0]
            etype = row[1]
            count = row[2]
            if day not in daily_data:
                daily_data[day] = {"intrusion": 0, "fall": 0, "face": 0, "counter": 0}
            daily_data[day][etype] = count
            
        # 3. Thống kê số lượng cảnh báo theo từng Camera
        camera_counts = db.query(SystemEventLog.camera_id, func.count(SystemEventLog.id)).group_by(SystemEventLog.camera_id).all()
        camera_summary = {c[0]: c[1] for c in camera_counts}
        
        return {
            "type_summary": type_summary,
            "daily_data": daily_data,
            "camera_summary": camera_summary
        }
    except Exception as e:
        print(f"[ANALYTICS] Lỗi tính toán thống kê: {e}")
        return {"error": str(e)}
    finally:
        db.close()

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
    check_admin(request)
        
    image_bytes = await file.read()
    
    # Sử dụng import lười để tránh circular import khi tải mô hình AI
    from app.ai import mtcnn_single, resnet, device
    
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    face = mtcnn_single(img)
    if face is None:
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt nào trong ảnh!")
        
    # Che khuất phần mặt dưới (45% từ dưới lên) để hỗ trợ nhận diện khẩu trang
    face[:, 88:, :] = 0.0
    face = face.unsqueeze(0).to(device)
    embedding = resnet(face).detach().cpu().numpy()[0]
    # Chuẩn hóa L2-norm trước khi lưu vào CSDL để tăng độ chính xác so khớp
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    emb_list = embedding.tolist()
    emb_json = json.dumps(emb_list)
    
    db = SessionLocal()
    from datetime import datetime
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_by = request.session.get("username", "System")
    new_face = FaceRecord(name=name, embedding=emb_json, created_at=created_at, created_by=created_by)
    db.add(new_face)
    db.commit()
    db.refresh(new_face)
    db.close()
    
    SystemStatus.add_log(f"Đăng ký khuôn mặt thành công: {name} (Bởi: {created_by})", "success")
    return {"message": "Đăng ký thành công!", "id": new_face.id, "name": new_face.name}

@app.get("/faces")
def get_all_faces(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401)
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    return [
        {
            "id": f.id, 
            "name": f.name,
            "created_at": f.created_at or "Không rõ",
            "created_by": f.created_by or "Không rõ"
        } for f in faces
    ]

@app.put("/faces/{face_id}")
async def update_face_name(face_id: int, request: Request):
    check_admin(request)
    
    payload = await request.json()
    new_name = payload.get("name")
    if not new_name or new_name.strip() == "":
        raise HTTPException(status_code=400, detail="Tên không được để trống!")
        
    db = SessionLocal()
    face = db.query(FaceRecord).filter(FaceRecord.id == face_id).first()
    if not face:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy khuôn mặt này.")
        
    old_name = face.name
    face.name = new_name.strip()
    try:
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã đổi tên khuôn mặt từ '{old_name}' thành '{new_name}'", "info")
        return {"message": "Đã đổi tên thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/faces/{face_id}")
def delete_face(face_id: int, request: Request):
    check_admin(request)
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
                "video_path": log.video_path,
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
    return [{"id": u.id, "username": u.username, "role": u.role or "admin"} for u in users]

@app.post("/api/users")
def create_user(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form("operator")):
    check_admin(request)
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Tài khoản này đã tồn tại!")
    new_user = User(username=username, password_hash=hash_password(password), role=role)
    try:
        db.add(new_user)
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã tạo tài khoản {role} mới: {username}", "success")
        return {"message": f"Đã tạo tài khoản {role} thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    check_admin(request)
    payload = await request.json()
    password = payload.get("password")
    role = payload.get("role")
    if not password and not role:
        raise HTTPException(status_code=400, detail="Thiếu thông tin cập nhật!")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng này!")
    if password:
        user.password_hash = hash_password(password)
    if role:
        user.role = role
    try:
        db.commit()
        db.close()
        SystemStatus.add_log(f"Đã cập nhật thông tin user ID: {user_id}", "info")
        return {"message": "Đã cập nhật thành công!"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, request: Request):
    check_admin(request)
    current_user_id = request.session.get("user_id")
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
    check_admin(request)
    new_cam = await request.json()
    camera_id = new_cam.get("camera_id")
    if not camera_id:
        raise HTTPException(status_code=400, detail="Thiếu Camera ID!")
    
    cameras = config.get_cameras_config()
    if any(c["camera_id"] == camera_id for c in cameras):
        raise HTTPException(status_code=400, detail="Camera ID này đã tồn tại!")
    
    # Thiết lập giá trị mặc định cho camera mới
    if "source" not in new_cam: new_cam["source"] = "video.mp4"
    if "features" not in new_cam: new_cam["features"] = ["intrusion_roi"]
    if "line" not in new_cam: new_cam["line"] = [[100, 180], [540, 180]]
    if "in_direction" not in new_cam: new_cam["in_direction"] = "down"
    if "roi" not in new_cam: new_cam["roi"] = [[100, 100], [540, 100], [540, 300], [100, 300]]
    if "schedule_enabled" not in new_cam: new_cam["schedule_enabled"] = False
    if "schedule_start" not in new_cam: new_cam["schedule_start"] = "23:00"
    if "schedule_end" not in new_cam: new_cam["schedule_end"] = "06:00"
    if "map_id" not in new_cam: new_cam["map_id"] = "khu_a_tang_1"
    if "trigger_alarm" not in new_cam: new_cam["trigger_alarm"] = False

    cameras.append(new_cam)
    config.save_full_cameras_config(cameras)
    ensure_camera_thread_running(camera_id)
    SystemStatus.add_log(f"Đã thêm camera mới: {camera_id}", "success")
    return {"message": "Đã thêm camera thành công!"}

@app.put("/api/cameras/{camera_id}")
async def update_camera(camera_id: str, request: Request):
    check_admin(request)
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
    stop_camera_thread(camera_id)
    ensure_camera_thread_running(camera_id)
    SystemStatus.add_log(f"Đã cập nhật camera: {camera_id}", "info")
    return {"message": "Đã cập nhật camera thành công!"}

@app.delete("/api/cameras/{camera_id}")
def delete_camera(camera_id: str, request: Request):
    check_admin(request)
    cameras = config.get_cameras_config()
    filtered_cameras = [c for c in cameras if c["camera_id"] != camera_id]
    if len(filtered_cameras) == len(cameras):
        raise HTTPException(status_code=404, detail="Không tìm thấy camera!")
    config.save_full_cameras_config(filtered_cameras)
    stop_camera_thread(camera_id)
    SystemStatus.add_log(f"Đã xóa camera: {camera_id}", "danger")
    return {"message": "Đã xóa camera thành công!"}

# =========================================================================
# ROUTING XEM LẠI VIDEO (CONTINUOUS RECORDINGS ENDPOINTS)
# =========================================================================
@app.get("/recordings", response_class=HTMLResponse)
def get_recordings_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "recordings.html", {"active_page": "recordings"})

@app.get("/api/recordings")
def get_recordings_api(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    
    recordings_dir = os.path.join("static", "recordings")
    os.makedirs(recordings_dir, exist_ok=True)
    
    from datetime import datetime
    recordings = []
    for f in os.listdir(recordings_dir):
        fp = os.path.join(recordings_dir, f)
        if os.path.isfile(fp) and (f.endswith(".mp4") or f.endswith(".avi")):
            mtime = os.path.getmtime(fp)
            size_bytes = os.path.getsize(fp)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            camera_id = "unknown"
            
            if f.startswith("recording_"):
                parts = f.split("_")
                if len(parts) >= 4:
                    camera_id = "_".join(parts[1:-2])
            
            recordings.append({
                "filename": f,
                "camera_id": camera_id,
                "timestamp": timestamp,
                "size_mb": size_mb,
                "video_path": f"/static/recordings/{f}"
            })
            
    recordings.sort(key=lambda x: x["timestamp"], reverse=True)
    return recordings

@app.delete("/api/recordings/{filename}")
def delete_recording_api(filename: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    check_admin(request)
    
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Tên tệp không hợp lệ!")
        
    fp = os.path.join("static", "recordings", filename)
    if os.path.exists(fp):
        try:
            os.remove(fp)
            SystemStatus.add_log(f"Đã xóa video lưu trữ: {filename}", "info")
            return {"message": "Xóa tệp thành công!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Không thể xóa tệp: {e}")
    else:
        raise HTTPException(status_code=404, detail="Tệp không tồn tại!")

@app.get("/api/test_gas_leak")
def test_gas_leak_api(active: bool, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    check_admin(request)
    
    SystemStatus.mock_gas_leak = active
    return {"message": f"Đã thiết lập trạng thái giả lập khí ga: {active}", "mock_gas_leak": active}

@app.post("/api/control_light")
async def control_light_api(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    payload = await request.json()
    state = payload.get("state", False)
    from app.processors import set_light_state
    set_light_state(state)
    return {"message": f"Đã {'BẬT' if state else 'TẮT'} đèn thành công!", "light_active": state}

@app.post("/api/settings/house_lock")
async def toggle_house_lock_route(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    check_admin(request)
    payload = await request.json()
    house_locked = payload.get("house_locked", False)
    config.settings["house_locked"] = house_locked
    config.save_settings()
    
    msg = "🔒 HỆ THỐNG: Đã KÍCH HOẠT chế độ KHÓA NHÀ (Arm)." if house_locked else "🔓 HỆ THỐNG: Đã TẮT chế độ KHÓA NHÀ (Disarm)."
    SystemStatus.add_log(msg, "warning" if house_locked else "info")
    return {"message": msg, "house_locked": house_locked}

@app.get("/api/test_buzzer")
def test_buzzer_api(active: bool, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    check_admin(request)
    SystemStatus.mock_buzzer = active
    return {"message": f"Đã thiết lập trạng thái giả lập còi báo động: {active}", "mock_buzzer": active}

@app.get("/api/play_recording")
def play_recording_stream(filepath: str, request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
        
    # Chuẩn hóa đường dẫn bằng cách loại bỏ dấu gạch chéo đầu tiên
    path_to_open = filepath.lstrip('/')
    if not (path_to_open.startswith("static/recordings") or path_to_open.startswith("static/alerts")):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập thư mục này!")
        
    if not os.path.exists(path_to_open):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp video!")
        
    from fastapi.responses import StreamingResponse
    import time
    import cv2
    
    def frame_generator():
        cap = cv2.VideoCapture(path_to_open)
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                ret_enc, jpeg_buf = cv2.imencode('.jpg', frame)
                if not ret_enc:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_buf.tobytes() + b'\r\n')
                # Giới hạn phát lại ở tốc độ ~15 FPS
                time.sleep(0.066)
        finally:
            cap.release()
            
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

