import os
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

# Cấu hình Secret Key dùng để ký và xác thực cookie tránh giả mạo
SECRET_KEY = b"MSE_SMART_CAMERA_SECRET_KEY_2026_FPT"
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
                        cookie_str = f"{COOKIE_NAME}={new_cookie_val}; Path=/; Max-Age={MAX_AGE}; HttpOnly; SameSite=Lax"
                        resp_headers.append("Set-Cookie", cookie_str)
                else:
                    # Nếu session bị xóa trống (khi đăng xuất), thực hiện xóa cookie ở client
                    if cookie_val:
                        cookie_str = f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
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

