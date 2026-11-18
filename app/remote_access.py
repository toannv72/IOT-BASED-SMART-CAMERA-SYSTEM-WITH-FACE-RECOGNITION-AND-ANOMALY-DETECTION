import os
import re
import sys
import time
import json
import shutil
import platform
import tempfile
import threading
import subprocess
import requests
from datetime import datetime
import app.config as config
from app.config import SystemStatus

# Trạng thái đường hầm truy cập từ xa (Remote Access Tunnel)
remote_tunnel_status = {
    "active": False,
    "starting": False,
    "public_url": "",
    "provider": "",
    "started_at": "",
    "last_error": ""
}

_tunnel_proc = None
_tunnel_lock = threading.Lock()


def _get_cloudflared_binary_path() -> str:
    """
    Tìm hoặc tự động tải tệp thực thi `cloudflared` chính thức của Cloudflare
    tương thích với Windows (x64) và Raspberry Pi / Linux (ARM64, ARMhf, x64).
    """
    is_win = sys.platform.startswith("win")
    local_bin = os.path.join(os.getcwd(), "cloudflared.exe" if is_win else "cloudflared")
    if os.path.exists(local_bin) and os.path.getsize(local_bin) > 1024 * 1024:
        return local_bin

    # Kiểm tra trong PATH hệ thống
    sys_bin = shutil.which("cloudflared")
    if sys_bin:
        return sys_bin

    # Tự động tải cloudflared nhẹ về thư mục dự án
    machine = platform.machine().lower()
    if is_win:
        dl_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    elif "aarch64" in machine or "arm64" in machine:
        dl_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif "arm" in machine:
        dl_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
    else:
        dl_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

    print(f"[REMOTE ACCESS] Đang tự động tải công cụ Cloudflare Tunnel từ: {dl_url} ...")
    SystemStatus.add_log("🌐 Truy cập từ xa: Đang tải công cụ Cloudflare Tunnel lần đầu...", "info")
    resp = requests.get(dl_url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(local_bin, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    if not is_win:
        try:
            os.chmod(local_bin, 0o755)
        except Exception:
            pass

    print(f"[REMOTE ACCESS] Đã tải hoàn tất công cụ Cloudflare Tunnel tại: {local_bin}")
    return local_bin


def notify_remote_url_to_telegram(public_url: str):
    """
    Tự động gửi đường link HTTPS xem camera từ xa về Telegram của Admin
    kèm nút bấm mở trực tiếp trên điện thoại (4G/5G/Wi-Fi ngoài).
    """
    token = config.settings.get("telegram_token", "").strip()
    chats = [str(x) for x in config.settings.get("telegram_chats", [])]
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN" or not chats:
        return

    text = (
        "🌐 *ĐƯỜNG LINK XEM CAMERA TRỰC TIẾP TỪ XA (4G / KHÁC MẠNG WI-FI)*\n\n"
        f"🔗 Link truy cập toàn cầu:\n{public_url}\n\n"
        "📱 *Hướng dẫn trên điện thoại:*\n"
        "• Bạn có thể dùng 4G/5G hoặc Wi-Fi ở bất kỳ nơi nào khác.\n"
        "• Bấm vào nút *Mở Web Xem Camera Trực Tiếp* bên dưới (hoặc mở link trên trình duyệt điện thoại) và đăng nhập tài khoản quản trị để xem Live Stream tất cả Camera!"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Mở Web Xem Camera Trực Tiếp (Live)", "url": public_url}],
            [{"text": "📹 Chụp Ảnh / Quay Video Qua Telegram", "callback_data": "open_cam_menu"}]
        ]
    }
    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in chats:
        try:
            requests.post(send_url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup)
            }, timeout=8)
        except Exception as e:
            print(f"[REMOTE ACCESS] Lỗi gửi link từ xa tới Telegram {chat_id}: {e}")


def start_remote_tunnel(port: int = 8000, notify_telegram: bool = True) -> dict:
    """
    Khởi chạy đường hầm đám mây (Cloudflare Quick Tunnel hoặc SSH localhost.run dự phòng)
    để tạo đường dẫn HTTPS công khai giúp điện thoại ở mạng khác (4G/5G) xem trực tiếp được Camera.
    """
    global _tunnel_proc
    with _tunnel_lock:
        if remote_tunnel_status["active"] and _tunnel_proc is not None and _tunnel_proc.poll() is None:
            if notify_telegram and remote_tunnel_status["public_url"]:
                threading.Thread(target=notify_remote_url_to_telegram, args=(remote_tunnel_status["public_url"],), daemon=True).start()
            return dict(remote_tunnel_status)

        if remote_tunnel_status["starting"]:
            return dict(remote_tunnel_status)

        remote_tunnel_status["starting"] = True
        remote_tunnel_status["last_error"] = ""

    def _tunnel_worker():
        global _tunnel_proc
        found_url = ""
        provider_name = "Cloudflare Tunnel"

        # 1. Thử khởi chạy bằng Cloudflare Quick Tunnel (Tốc độ cao, hỗ trợ MJPEG video stream mượt mà)
        try:
            cf_bin = _get_cloudflared_binary_path()
            cmd = [cf_bin, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags
            )
            with _tunnel_lock:
                _tunnel_proc = proc

            start_wait = time.time()
            url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
            while time.time() - start_wait < 25:
                if proc.poll() is not None:
                    break
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                m = url_pattern.search(line)
                if m:
                    found_url = m.group(0)
                    break
        except Exception as cf_err:
            print(f"[REMOTE ACCESS] Cloudflare Tunnel gặp lỗi ({cf_err}), chuyển sang SSH Tunnel dự phòng...")

        # 2. Nếu Cloudflare Tunnel không lấy được link, fallback sang SSH Reverse Tunnel (localhost.run)
        if not found_url:
            try:
                provider_name = "SSH Cloud Tunnel (localhost.run)"
                ssh_bin = shutil.which("ssh")
                if ssh_bin:
                    cmd_ssh = [
                        ssh_bin,
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ServerAliveInterval=30",
                        "-R", f"80:127.0.0.1:{port}",
                        "nokey@localhost.run"
                    ]
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                    proc = subprocess.Popen(
                        cmd_ssh,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=creationflags
                    )
                    with _tunnel_lock:
                        _tunnel_proc = proc

                    start_wait = time.time()
                    ssh_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.lhr\.life")
                    while time.time() - start_wait < 20:
                        if proc.poll() is not None:
                            break
                        line = proc.stdout.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        m = ssh_pattern.search(line)
                        if m:
                            found_url = m.group(0)
                            break
            except Exception as ssh_err:
                print(f"[REMOTE ACCESS] SSH Tunnel lỗi: {ssh_err}")

        with _tunnel_lock:
            remote_tunnel_status["starting"] = False
            if found_url:
                remote_tunnel_status["active"] = True
                remote_tunnel_status["public_url"] = found_url
                remote_tunnel_status["provider"] = provider_name
                remote_tunnel_status["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                remote_tunnel_status["last_error"] = ""
                print(f"[REMOTE ACCESS] ✅ Đã mở đường hầm truy cập từ xa thành công: {found_url}")
                SystemStatus.add_log(f"🌐 Truy cập từ xa (4G/Internet) đã bật: {found_url}", "success")
            else:
                remote_tunnel_status["active"] = False
                remote_tunnel_status["public_url"] = ""
                remote_tunnel_status["last_error"] = "Không thể khởi tạo đường hầm đám mây. Hãy kiểm tra kết nối mạng Internet!"
                SystemStatus.add_log("⚠️ Không thể khởi tạo đường hầm truy cập từ xa.", "danger")
                if _tunnel_proc is not None:
                    try:
                        _tunnel_proc.terminate()
                    except Exception:
                        pass
                    _tunnel_proc = None
                return

        if notify_telegram and found_url:
            notify_remote_url_to_telegram(found_url)

        # Tiếp tục đọc stdout ngầm để giữ tiến trình đường hầm không bị đầy pipe buffer
        try:
            proc_ref = _tunnel_proc
            while proc_ref and proc_ref.poll() is None:
                line = proc_ref.stdout.readline()
                if not line:
                    time.sleep(0.5)
        except Exception:
            pass
        finally:
            with _tunnel_lock:
                if _tunnel_proc == proc_ref:
                    remote_tunnel_status["active"] = False
                    remote_tunnel_status["public_url"] = ""

    threading.Thread(target=_tunnel_worker, daemon=True, name="RemoteAccessTunnel").start()

    # Đợi tối đa 15 giây để trả về ngay đường link nếu khởi tạo kịp trong HTTP request
    wait_start = time.time()
    while time.time() - wait_start < 15.0:
        with _tunnel_lock:
            if not remote_tunnel_status["starting"]:
                break
        time.sleep(0.3)

    return dict(remote_tunnel_status)


def stop_remote_tunnel() -> dict:
    """
    Tắt đường hầm truy cập từ xa.
    """
    global _tunnel_proc
    with _tunnel_lock:
        if _tunnel_proc is not None:
            try:
                _tunnel_proc.terminate()
            except Exception:
                pass
            _tunnel_proc = None
        remote_tunnel_status["active"] = False
        remote_tunnel_status["starting"] = False
        remote_tunnel_status["public_url"] = ""
        SystemStatus.add_log("🔒 Đã đóng đường hầm truy cập từ xa.", "warning")
        return dict(remote_tunnel_status)


def get_remote_tunnel_status() -> dict:
    with _tunnel_lock:
        if _tunnel_proc is not None and _tunnel_proc.poll() is not None:
            remote_tunnel_status["active"] = False
            remote_tunnel_status["public_url"] = ""
        return dict(remote_tunnel_status)


def send_live_camera_snapshot_to_telegram(token: str, chat_id: str, camera_id: str):
    """
    Chụp tức thời khung hình trực tiếp hiện tại của `camera_id` và gửi về điện thoại qua Telegram.
    """
    import cv2
    from app.processors import camera_states, ensure_camera_thread_running
    ensure_camera_thread_running(camera_id)

    state = camera_states.get(camera_id)
    jpeg_bytes = None
    if state is not None:
        if getattr(state, "last_jpeg_frame", None) is not None:
            jpeg_bytes = state.last_jpeg_frame
        elif getattr(state, "last_frame", None) is not None:
            ok, buf = cv2.imencode(".jpg", state.last_frame)
            if ok:
                jpeg_bytes = buf.tobytes()

    if not jpeg_bytes:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"⚠️ Camera '{camera_id}' hiện chưa sẵn sàng hoặc đang tạm dừng!"
        }, timeout=8)
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = f"📸 *[ẢNH TRỰC TIẾP TỪ XA]*\n• Camera: `{camera_id}`\n• Thời điểm: `{now_str}`"
    files = {"photo": (f"live_{camera_id}.jpg", jpeg_bytes, "image/jpeg")}
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔄 Chụp Lại Ảnh Mới", "callback_data": f"tg_snap_{camera_id}"},
                {"text": "🎬 Quay Video Live 5s", "callback_data": f"tg_clip_{camera_id}"}
            ],
            [{"text": "📹 Danh Sách Camera", "callback_data": "open_cam_menu"}]
        ]
    }
    requests.post(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data={
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        },
        files=files,
        timeout=15
    )


def send_live_camera_clip_to_telegram(token: str, chat_id: str, camera_id: str, duration_sec: int = 5):
    """
    Thu trực tiếp một đoạn video ngắn (5 giây) từ luồng trực tiếp của `camera_id`
    và gửi thẳng về ứng dụng Telegram trên điện thoại để xem từ xa qua 4G/5G.
    """
    def _clip_worker():
        import cv2
        from app.processors import camera_states, ensure_camera_thread_running
        ensure_camera_thread_running(camera_id)

        state = camera_states.get(camera_id)
        if state is None:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"⚠️ Camera '{camera_id}' hiện chưa hoạt động!"
            }, timeout=8)
            return

        # Thông báo đang thu hình trực tiếp
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"🎬 Đang ghi hình trực tiếp {duration_sec} giây từ camera *{camera_id}*... Vui lòng đợi trong giây lát!",
            "parse_mode": "Markdown"
        }, timeout=5)

        frames = []
        fps = 10.0
        interval = 1.0 / fps
        total_frames = int(duration_sec * fps)
        for _ in range(total_frames):
            f = getattr(state, "paced_frame", None)
            if f is None:
                f = getattr(state, "last_frame", None)
            if f is not None:
                frames.append(f.copy())
            time.sleep(interval)

        if not frames:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"⚠️ Không thu được khung hình nào từ camera '{camera_id}'!"
            }, timeout=8)
            return

        tmp_path = os.path.join(tempfile.gettempdir(), f"live_{camera_id}_{int(time.time())}.mp4")
        try:
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            if sys.platform.startswith("win"):
                out = cv2.VideoWriter(tmp_path, cv2.CAP_MSMF, fourcc, fps, (640, 360))
            else:
                out = cv2.VideoWriter(tmp_path, fourcc, fps, (640, 360))
            if not out.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(tmp_path, fourcc, fps, (640, 360))
            for frame in frames:
                if frame.shape[0] != 360 or frame.shape[1] != 640:
                    frame = cv2.resize(frame, (640, 360))
                out.write(frame)
            out.release()

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            caption = f"🎬 *[VIDEO TRỰC TIẾP TỪ XA - {duration_sec} GIÂY]*\n• Camera: `{camera_id}`\n• Thời điểm: `{now_str}`"
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🎬 Quay Tiếp 5s", "callback_data": f"tg_clip_{camera_id}"},
                        {"text": "📸 Chụp Ảnh Tức Thời", "callback_data": f"tg_snap_{camera_id}"}
                    ],
                    [{"text": "🌐 Lấy Link Xem Live Toàn Màn Hình", "callback_data": "tg_get_live_link"}]
                ]
            }
            with open(tmp_path, "rb") as vf:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendVideo",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "Markdown",
                        "supports_streaming": "true",
                        "reply_markup": json.dumps(keyboard)
                    },
                    files={"video": (os.path.basename(tmp_path), vf, "video/mp4")},
                    timeout=45
                )
        except Exception as e:
            print(f"[REMOTE ACCESS] Lỗi gửi video trực tiếp qua Telegram: {e}")
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    threading.Thread(target=_clip_worker, daemon=True, name=f"TgLiveClip_{camera_id}").start()
