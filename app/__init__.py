import os
import sys

# Khống chế số luồng OpenMP / MKL / OpenBLAS trước khi nạp NumPy / PyTorch / OpenCV
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
os.environ.setdefault("KMP_BLOCKTIME", "0")

# Khắc phục lỗi UnicodeEncodeError khi in tiếng Việt/ký tự lạ ra cửa sổ terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='backslashreplace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(errors='backslashreplace')
    except Exception:
        pass

import json
import hmac
import hashlib
import base64
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

# Tạo thư mục static/alerts nếu chưa tồn tại
os.makedirs("static/alerts", exist_ok=True)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Unified Smart Surveillance Dashboard")

# Cấu hình Secret Key động dùng để ký và xác thực cookie tránh giả mạo
import secrets as _secrets
def _load_or_create_secret_key() -> bytes:
    env_key = os.environ.get("SMARTCAM_SECRET_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")
    key_file = ".secret_key"
    if os.path.exists(key_file):
        try:
            with open(key_file, "rb") as kf:
                data = kf.read().strip()
                if len(data) >= 32:
                    return data
        except Exception:
            pass
    new_key = _secrets.token_hex(32).encode("utf-8")
    try:
        with open(key_file, "wb") as kf:
            kf.write(new_key)
    except Exception:
        pass
    return new_key

SECRET_KEY = _load_or_create_secret_key()
COOKIE_NAME = "surveillance_session"
MAX_AGE = 14400  # 4 tiếng (14400 giây)

def sign_data_with_key(data_str: str, key: bytes) -> str:
    """Ký số dữ liệu bằng HMAC-SHA256"""
    signature = hmac.new(key, data_str.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{data_str}.{signature}"

def verify_data_with_key(signed_str: str, key: bytes) -> str:
    """Xác thực chữ ký số HMAC-SHA256 và trả về dữ liệu gốc nếu hợp lệ"""
    try:
        if "." not in signed_str:
            return None
        data_str, signature = signed_str.rsplit('.', 1)
        expected_signature = hmac.new(key, data_str.encode('utf-8'), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return data_str
    except Exception:
        pass
    return None

class HMACSessionMiddleware:
    """
    Middleware ASGI tự phát triển thay thế SessionMiddleware của Starlette.
    Sử dụng chữ ký số HMAC-SHA256 với thư viện chuẩn của Python để lưu trữ session an toàn trong cookie
    mà không cần cài đặt thêm thư viện ngoài (như 'itsdangerous').
    """
    def __init__(self, app_ins):
        self.app = app_ins

    async def __call__(self, scope, receive, send):
        # Chỉ xử lý các yêu cầu HTTP và Websocket
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 1. Trích xuất cookies từ headers của HTTP Request
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode("utf-8")
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies[k] = v

        # 2. Giải mã và kiểm tra tính hợp lệ của session cookie
        cookie_val = cookies.get(COOKIE_NAME)
        session_data = {}
        initial_session_str = ""
        if cookie_val:
            verified_b64 = verify_data_with_key(cookie_val, SECRET_KEY)
            if verified_b64:
                try:
                    session_json = base64.b64decode(verified_b64.encode('utf-8')).decode('utf-8')
                    session_data = json.loads(session_json)
                    initial_session_str = session_json
                except Exception:
                    session_data = {}

        # Gán session vào scope để FastAPI Request có thể truy cập qua request.session
        scope["session"] = session_data

        # Chặn truy cập ẩn danh vào ảnh cảnh báo & video lưu trữ trong /static/alerts và /static/recordings
        req_path = scope.get("path", "")
        if (req_path.startswith("/static/alerts/") or req_path.startswith("/static/recordings/")) and not session_data.get("user_id"):
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            })
            await send({
                "type": "http.response.body",
                "body": b"Unauthorized",
            })
            return

        is_https = (scope.get("scheme") == "https") or (
            headers.get(b"x-forwarded-proto", b"").decode("utf-8", "ignore").lower() == "https"
        )
        secure_attr = "; Secure" if is_https else ""

        # 3. Tạo một send wrapper để kiểm tra sự thay đổi của session và thiết lập cookie phản hồi
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                current_session = scope.get("session", {})
                current_session_json = json.dumps(current_session)
                
                resp_headers = MutableHeaders(scope=message)
                
                if current_session:
                    # Nếu dữ liệu session bị thay đổi, thực hiện ghi đè cookie mới
                    if current_session_json != initial_session_str:
                        new_b64 = base64.b64encode(current_session_json.encode('utf-8')).decode('utf-8')
                        new_cookie_val = sign_data_with_key(new_b64, SECRET_KEY)
                        cookie_str = f"{COOKIE_NAME}={new_cookie_val}; Path=/; Max-Age={MAX_AGE}; HttpOnly; SameSite=Lax{secure_attr}"
                        resp_headers.append("Set-Cookie", cookie_str)
                else:
                    # Nếu session bị xóa trống (khi đăng xuất), thực hiện xóa cookie ở client
                    if cookie_val:
                        cookie_str = f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure_attr}"
                        resp_headers.append("Set-Cookie", cookie_str)

            await send(message)

        await self.app(scope, receive, send_wrapper)

# Đăng ký custom HMACSessionMiddleware vào ứng dụng
app.add_middleware(HMACSessionMiddleware)

# Cấu hình thư mục static để phục vụ việc xem ảnh chụp cảnh báo từ trình duyệt
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import các routes để đăng ký vào app (tránh circular imports bằng cách import ở cuối)
from app import routes

# Khởi chạy luồng tự động dọn dẹp hệ thống chạy ngầm
from app.cleanup import start_cleanup_thread
start_cleanup_thread()

# Khởi chạy luồng xử lý camera chạy ngầm 24/7
from app.processors import start_all_camera_threads
start_all_camera_threads()

# Tự động mở đường hầm truy cập từ xa (4G/Internet) nếu được bật trong cấu hình
import app.config as _cfg
if _cfg.settings.get("remote_access_auto_start", False):
    import threading as _th
    def _auto_remote():
        import time as _t
        _t.sleep(4)
        from app.remote_access import start_remote_tunnel
        start_remote_tunnel(port=8000, notify_telegram=True)
    _th.Thread(target=_auto_remote, daemon=True, name="AutoRemoteTunnel").start()

