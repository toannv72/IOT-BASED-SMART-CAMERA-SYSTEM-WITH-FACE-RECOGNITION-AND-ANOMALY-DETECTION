import os
import re
import time
import base64
import mimetypes
import threading
import requests
from datetime import datetime
import app.config as config
from app.config import SystemStatus
from app.database import SessionLocal, SystemEventLog

# Trạng thái hoạt động thời gian thực của phân hệ Google Drive & Chuỗi Dự Phòng (Failover)
gdrive_runtime_status = {
    "last_sync_time": "Chưa đồng bộ",
    "last_cleanup_time": "Chưa dọn dẹp",
    "total_uploaded": 0,
    "total_deleted": 0,
    "failover_count": 0,
    "active_target": "Chưa kích hoạt",
    "last_file_url": "",
    "folder_url": "",
    "last_error": "",
    "last_db_backup_ts": 0.0
}

_synced_recordings = set()
_gdrive_lock = threading.Lock()


def extract_folder_id(folder_input: str) -> str:
    """
    Trích xuất mã Folder ID từ đường dẫn URL Google Drive hoặc chuỗi ID trực tiếp.
    Hỗ trợ các dạng:
    - https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz?usp=sharing
    - https://drive.google.com/drive/u/0/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
    - https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWxYz
    - 1AbCdEfGhIjKlMnOpQrStUvWxYz
    """
    if not folder_input:
        return ""
    s = folder_input.strip()
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1)
    m2 = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", s)
    if m2:
        return m2.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{10,}$", s):
        return s
    return ""


def post_to_gdrive_webhook(payload: dict, timeout: int = 45, custom_webhook_url: str = None) -> dict:
    """
    Gửi yêu cầu HTTP POST tới Google Apps Script Web App URL.
    Hỗ trợ truyền `custom_webhook_url` cho các Link Google Drive Dự phòng (Link #2, #3...).
    """
    webhook_url = (custom_webhook_url or config.settings.get("gdrive_webhook_url", "")).strip()
    if not webhook_url:
        return {"status": "error", "message": "Chưa cấu hình Google Drive Webhook URL!"}

    if not (webhook_url.startswith("https://script.google.com/") or webhook_url.startswith("http")):
        return {"status": "error", "message": "Đường dẫn Webhook URL không hợp lệ!"}

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=timeout
        )
        if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
            resp = requests.get(resp.headers["Location"], timeout=timeout)

        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return {
                    "status": "error",
                    "message": "Phản hồi từ Google Apps Script không phải JSON hợp lệ. Hãy kiểm tra quyền truy cập Web App là 'Bất kỳ ai (Anyone)'!"
                }
        else:
            return {
                "status": "error",
                "message": f"Google Apps Script trả về mã lỗi HTTP {resp.status_code}"
            }
    except Exception as e:
        return {"status": "error", "message": f"Lỗi kết nối tới Google Drive Webhook: {e}"}


def get_target_drive_params() -> tuple:
    """
    Trả về (folder_id, folder_name) của Link Google Drive Chính (#1).
    """
    mode = config.settings.get("gdrive_target_mode", "auto_folder")
    folder_name = (config.settings.get("gdrive_folder_name", "SmartCamera_Cloud_Backup") or "SmartCamera_Cloud_Backup").strip()
    raw_folder_id = config.settings.get("gdrive_folder_id", "")
    if mode == "custom_folder" or raw_folder_id.strip():
        fid = extract_folder_id(raw_folder_id) if mode == "custom_folder" else ""
        return fid, folder_name
    return "", folder_name


def get_all_drive_targets() -> list:
    """
    Xây dựng danh sách chuỗi các đích lưu trữ Google Drive theo thứ tự ưu tiên (Failover Chain):
    1. Link Google Drive Chính (#1)
    2. Danh sách các Link Google Drive Dự phòng (#2, #3...) trong `gdrive_backup_links`
    """
    targets = []
    primary_webhook = config.settings.get("gdrive_webhook_url", "").strip()
    fid_1, fname_1 = get_target_drive_params()
    if primary_webhook:
        targets.append({
            "index": 1,
            "name": "Link Drive Chính (#1)",
            "webhook_url": primary_webhook,
            "folder_id": fid_1,
            "folder_name": fname_1
        })

    backup_links = config.settings.get("gdrive_backup_links", []) or []
    for idx, item in enumerate(backup_links, start=2):
        if not isinstance(item, dict) or item.get("enabled", True) is False:
            continue
        wh = str(item.get("webhook_url", "") or "").strip() or primary_webhook
        raw_fid = str(item.get("folder_id", "") or "").strip()
        fid = extract_folder_id(raw_fid)
        b_name = str(item.get("name", "") or f"Link Drive Dự Phòng (#{idx})").strip()
        folder_name = str(item.get("folder_name", "") or f"SmartCamera_Backup_{idx}").strip()
        if wh:
            targets.append({
                "index": idx,
                "name": b_name,
                "webhook_url": wh,
                "folder_id": fid,
                "folder_name": folder_name
            })
    return targets


def check_gdrive_folder_permission(folder_input: str = None, folder_name: str = None, target_mode: str = None, custom_webhook_url: str = None) -> dict:
    """
    Kiểm tra kết nối, dung lượng trống và quyền ghi (Write/Edit permission) vào thư mục trên Google Drive.
    """
    mode = target_mode or config.settings.get("gdrive_target_mode", "auto_folder")
    fname = (folder_name or config.settings.get("gdrive_folder_name", "SmartCamera_Cloud_Backup") or "SmartCamera_Cloud_Backup").strip()
    raw_fid = folder_input if folder_input is not None else config.settings.get("gdrive_folder_id", "")
    fid = extract_folder_id(raw_fid) if (mode == "custom_folder" or (folder_input and extract_folder_id(raw_fid))) else ""

    if mode == "custom_folder" and not fid:
        return {
            "status": "error",
            "message": "Đường link hoặc mã Folder ID thư mục Google Drive không hợp lệ! Hãy copy đường link dạng https://drive.google.com/drive/folders/1AbCdEf..."
        }

    payload = {
        "action": "check_folder",
        "folder_id": fid,
        "folder_name": fname,
        "min_free_mb": int(config.settings.get("gdrive_min_free_mb", 100))
    }
    res = post_to_gdrive_webhook(payload, timeout=30, custom_webhook_url=custom_webhook_url)
    if res.get("status") in ("ok", "full"):
        with _gdrive_lock:
            if res.get("folder_url"):
                gdrive_runtime_status["folder_url"] = res["folder_url"]
        return res

    err_msg = res.get("message", "Không thể truy cập thư mục Google Drive.")
    if "Action không hợp lệ" in err_msg:
        return {
            "status": "ok",
            "folder_name": fname if not fid else f"Folder ID: {fid}",
            "can_write": True,
            "message": "Kết nối Webhook thành công! (Hãy cập nhật mã Apps Script mới nhất trong phần Hướng dẫn để kiểm tra dung lượng trống tự động)."
        }
    return {
        "status": "error",
        "message": (
            f"Không thể truy cập hoặc ghi vào thư mục chỉ định ({err_msg}).\n"
            "👉 Nếu thư mục này thuộc tài khoản Google khác: Hãy bấm Chuột phải vào thư mục trên Google Drive -> Chia sẻ (Share) -> Cấp quyền 'Người chỉnh sửa (Editor)' cho tài khoản chạy Apps Script!"
        )
    }


def upload_bytes_to_gdrive(file_bytes: bytes, filename: str, mime_type: str = "image/jpeg", subfolder: str = "", ensure_local_fallback: bool = True) -> tuple:
    """
    Đẩy mảng bytes của tệp lên Google Drive theo Cơ chế Chuyển Tiếp Dự Phòng Đa Tầng (Failover Chain):
    - Bước 1: Thử đẩy vào Link Google Drive Chính (#1).
    - Bước 2: Nếu Link #1 đầy dung lượng (status='full' hoặc dưới ngưỡng `gdrive_min_free_mb`) hoặc lỗi,
              TỰ ĐỘNG chuyển sang Link Google Drive Dự phòng #2, #3...
    - Bước 3: Nếu tất cả các Link Google Drive đều không đủ dung lượng hoặc mất kết nối,
              TỰ ĐỘNG lưu giữ dự phòng vào Ổ cứng cục bộ (Chính -> Dự phòng).
    Trả về (success: bool, file_url: str, message: str)
    """
    targets = get_all_drive_targets()
    retention_days = int(config.settings.get("gdrive_retention_days", 30))
    min_free_mb = int(config.settings.get("gdrive_min_free_mb", 100))
    b64_data = base64.b64encode(file_bytes).decode("ascii")

    errors_log = []
    for idx, target in enumerate(targets):
        payload = {
            "action": "upload",
            "folder_id": target["folder_id"],
            "folder_name": target["folder_name"],
            "subfolder": subfolder,
            "filename": filename,
            "mime_type": mime_type,
            "file_base64": b64_data,
            "retention_days": retention_days,
            "min_free_mb": min_free_mb
        }

        res = post_to_gdrive_webhook(payload, timeout=60, custom_webhook_url=target["webhook_url"])
        status = res.get("status")

        if status == "ok":
            file_url = res.get("file_url", "")
            folder_url = res.get("folder_url", "")
            target_label = target["name"]
            if idx > 0:
                # Đã chuyển tiếp thành công sang Link Drive Dự Phòng
                with _gdrive_lock:
                    gdrive_runtime_status["failover_count"] += 1
                failover_notice = f" (Đã tự động chuyển tiếp dự phòng sang {target_label} do link trước đầy/lỗi)"
                SystemStatus.add_log(f"🔄 Google Drive Failover: Link chính đầy/lỗi -> Đã tự động lưu sang '{target_label}'!", "warning")
            else:
                failover_notice = ""

            with _gdrive_lock:
                gdrive_runtime_status["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                gdrive_runtime_status["total_uploaded"] += 1
                gdrive_runtime_status["active_target"] = target_label
                if file_url:
                    gdrive_runtime_status["last_file_url"] = file_url
                if folder_url:
                    gdrive_runtime_status["folder_url"] = folder_url
                gdrive_runtime_status["last_error"] = ""

            base_msg = res.get("message", f"Đã đẩy tệp lên {target_label} thành công!")
            return True, file_url, base_msg + failover_notice

        # Nếu link này báo đầy ('full') hoặc lỗi ('error'), ghi nhận và tự động thử link tiếp theo!
        reason = res.get("message", "Không đủ dung lượng hoặc mất kết nối")
        errors_log.append(f"{target['name']}: {reason}")
        print(f"[GDRIVE FAILOVER] ⚠️ {target['name']} không thể lưu ({reason}). Đang chuyển sang đích dự phòng tiếp theo...")

    # Nếu tất cả các Link Google Drive đều không đủ chỗ hoặc lỗi -> Chuyển về Lưu Dự Phòng Ổ Cứng Cục Bộ
    err_summary = " | ".join(errors_log) if errors_log else "Chưa cấu hình Link Google Drive"
    local_saved_path = ""
    if ensure_local_fallback:
        try:
            fallback_dir = os.path.join(config.get_storage_base_dir(), "cloud_fallback")
            if subfolder:
                fallback_dir = os.path.join(fallback_dir, subfolder)
            os.makedirs(fallback_dir, exist_ok=True)
            local_saved_path = os.path.join(fallback_dir, filename)
            with open(local_saved_path, "wb") as f:
                f.write(file_bytes)
        except Exception as loc_err:
            print(f"[GDRIVE FAILOVER] Lỗi ghi fallback ổ cứng: {loc_err}")

    with _gdrive_lock:
        gdrive_runtime_status["failover_count"] += 1
        gdrive_runtime_status["active_target"] = f"Ổ cứng dự phòng ({os.path.abspath(config.get_storage_base_dir())})"
        gdrive_runtime_status["last_error"] = err_summary

    if local_saved_path:
        SystemStatus.add_log(
            f"💾 Dự phòng Ổ cứng: Các Link Google Drive đều đầy/lỗi -> Đã tự động giữ tệp '{filename}' tại ổ cứng ({local_saved_path}).",
            "warning"
        )
        return False, "", f"Tất cả Link Google Drive đều đầy/lỗi ({err_summary}). Đã tự động lưu dự phòng an toàn vào ổ cứng tại: {local_saved_path}"

    return False, "", f"Không thể đẩy lên các Link Google Drive: {err_summary}"


def upload_file_to_gdrive(local_path: str, subfolder: str = None, custom_filename: str = None) -> tuple:
    """
    Đọc tệp từ ổ cứng cục bộ và đẩy lên chuỗi Google Drive (Chính -> Dự phòng).
    Nếu tất cả Link Drive đều đầy, tệp gốc tại `local_path` trên ổ cứng vẫn được giữ nguyên an toàn.
    """
    if not local_path or not os.path.exists(local_path):
        return False, "", f"Không tìm thấy tệp cục bộ: {local_path}"

    filename = custom_filename or os.path.basename(local_path)
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        if filename.endswith(".mp4"):
            mime_type = "video/mp4"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"

    if subfolder is None:
        if config.settings.get("gdrive_organize_by_date", True):
            subfolder = datetime.now().strftime("%Y-%m-%d")
        else:
            subfolder = ""

    try:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
        # Tệp đã nằm sẵn trên ổ cứng tại local_path nên không cần ghi lặp bản sao thứ 2 trừ khi cần
        ok, file_url, msg = upload_bytes_to_gdrive(file_bytes, filename, mime_type=mime_type, subfolder=subfolder, ensure_local_fallback=False)
        if not ok:
            with _gdrive_lock:
                gdrive_runtime_status["active_target"] = f"Ổ cứng cục bộ ({os.path.abspath(os.path.dirname(local_path))})"
            SystemStatus.add_log(
                f"💾 Dự phòng Ổ cứng: Các Link Drive không đủ chỗ -> Giữ nguyên tệp sự cố tại ổ cứng ({local_path}).",
                "warning"
            )
        return ok, file_url, msg
    except Exception as e:
        return False, "", f"Lỗi đọc tệp cục bộ {local_path}: {e}"


def sync_alert_event_to_gdrive(event_id: int, img_local_path: str = None, video_local_path: str = None, camera_id: str = "Unknown", alert_type: str = "intrusion"):
    """
    Hàm chạy ngầm bất đồng bộ: Tự động đẩy ảnh chụp và video sự cố lên chuỗi Google Drive (Link 1 -> Link 2... -> Ổ cứng).
    """
    if not config.settings.get("gdrive_enabled", False):
        return
    if not config.settings.get("gdrive_sync_alerts", True):
        return
    if not get_all_drive_targets():
        return

    def _worker():
        subfolder = datetime.now().strftime("%Y-%m-%d") if config.settings.get("gdrive_organize_by_date", True) else ""
        best_drive_link = ""

        # 1. Đẩy ảnh chụp cảnh báo
        if img_local_path and os.path.exists(img_local_path):
            ok_img, url_img, msg_img = upload_file_to_gdrive(img_local_path, subfolder=subfolder)
            if ok_img and url_img:
                best_drive_link = url_img
                print(f"[GDRIVE] Đã tải ảnh sự cố lên Google Drive: {url_img}")
            else:
                print(f"[GDRIVE] Ảnh sự cố được giữ tại ổ cứng dự phòng: {msg_img}")

        # 2. Đẩy video clip sự cố
        if video_local_path and os.path.exists(video_local_path):
            ok_vid, url_vid, msg_vid = upload_file_to_gdrive(video_local_path, subfolder=subfolder)
            if ok_vid and url_vid:
                best_drive_link = url_vid
                print(f"[GDRIVE] Đã tải video sự cố lên Google Drive: {url_vid}")
            else:
                print(f"[GDRIVE] Video sự cố được giữ tại ổ cứng dự phòng: {msg_vid}")

        # 3. Cập nhật đường dẫn Google Drive vào cơ sở dữ liệu SQLite
        if best_drive_link and event_id:
            db = SessionLocal()
            try:
                ev = db.query(SystemEventLog).filter(SystemEventLog.id == event_id).first()
                if ev:
                    ev.drive_link = best_drive_link
                    db.commit()
                active_t = gdrive_runtime_status.get("active_target", "Google Drive")
                SystemStatus.add_log(f"☁️ Đám mây ({active_t}): Đã sao lưu sự cố '{alert_type}' ({camera_id}).", "info")
            except Exception as e:
                db.rollback()
                print(f"[GDRIVE] Lỗi cập nhật drive_link vào SQLite: {e}")
            finally:
                db.close()

    threading.Thread(target=_worker, daemon=True, name="GDriveAlertSync").start()


def cleanup_gdrive_expired_files(retention_days: int = None) -> tuple:
    """
    Quét và xóa các tệp quá hạn (`retention_days`) trên TẤT CẢ các Link Google Drive trong chuỗi (Chính + Dự phòng).
    """
    if retention_days is None:
        retention_days = int(config.settings.get("gdrive_retention_days", 30))
    targets = get_all_drive_targets()
    if not targets:
        return False, 0, "Chưa cấu hình Link Google Drive nào!"

    total_deleted = 0
    any_ok = False
    messages = []

    for target in targets:
        payload = {
            "action": "cleanup",
            "folder_id": target["folder_id"],
            "folder_name": target["folder_name"],
            "retention_days": max(1, retention_days)
        }
        res = post_to_gdrive_webhook(payload, timeout=60, custom_webhook_url=target["webhook_url"])
        if res.get("status") == "ok":
            any_ok = True
            cnt = int(res.get("deleted_count", 0))
            total_deleted += cnt
            messages.append(f"{target['name']}: xóa {cnt} tệp")
        else:
            messages.append(f"{target['name']}: lỗi ({res.get('message', 'Không xác định')})")

    if any_ok:
        with _gdrive_lock:
            gdrive_runtime_status["last_cleanup_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            gdrive_runtime_status["total_deleted"] += total_deleted
            gdrive_runtime_status["last_error"] = ""
        summary_msg = f"Đã dọn dẹp tổng cộng {total_deleted} tệp quá hạn (> {retention_days} ngày) trên các Link Drive ({', '.join(messages)})."
        if total_deleted > 0:
            SystemStatus.add_log(f"🧹 Google Drive: {summary_msg}", "info")
        return True, total_deleted, summary_msg
    else:
        err_msg = "Không thể dọn dẹp trên các Link Drive: " + "; ".join(messages)
        with _gdrive_lock:
            gdrive_runtime_status["last_error"] = err_msg
        return False, 0, err_msg


def test_failover_chain() -> dict:
    """
    Kiểm tra toàn bộ Chuỗi Lưu Trữ Dự Phòng (Failover Chain):
    1. Kiểm tra lần lượt Link Google Drive Chính (#1) -> Các Link Google Drive Dự phòng (#2, #3...)
    2. Kiểm tra Ổ cứng cục bộ Chính -> Ổ cứng cục bộ Dự phòng.
    Trả về báo cáo chi tiết từng tầng lưu trữ.
    """
    tiers_report = []
    min_free_mb = int(config.settings.get("gdrive_min_free_mb", 100))

    # 1. Kiểm tra các tầng Google Drive
    drive_targets = get_all_drive_targets()
    for t in drive_targets:
        res = check_gdrive_folder_permission(
            folder_input=t["folder_id"],
            folder_name=t["folder_name"],
            target_mode="custom_folder" if t["folder_id"] else "auto_folder",
            custom_webhook_url=t["webhook_url"]
        )
        st = res.get("status")
        free_mb = res.get("free_mb")
        free_str = f" (Trống ~{free_mb} MB)" if free_mb is not None else ""
        if st == "ok":
            tiers_report.append({
                "tier": f"☁️ Tầng Đám Mây #{t['index']}: {t['name']}",
                "status": "ready",
                "detail": f"✅ Sẵn sàng ghi vào thư mục '{res.get('folder_name', t['folder_name'])}'{free_str}"
            })
        elif st == "full":
            tiers_report.append({
                "tier": f"☁️ Tầng Đám Mây #{t['index']}: {t['name']}",
                "status": "full",
                "detail": f"⚠️ Đã đầy dung lượng (< {min_free_mb} MB){free_str} -> Sẽ tự động chuyển sang tầng kế tiếp!"
            })
        else:
            tiers_report.append({
                "tier": f"☁️ Tầng Đám Mây #{t['index']}: {t['name']}",
                "status": "error",
                "detail": f"❌ Lỗi kết nối / Quyền: {res.get('message', 'Không xác định')} -> Sẽ tự động chuyển sang tầng kế tiếp!"
            })

    # 2. Kiểm tra Ổ cứng cục bộ Chính
    pri_raw = str(config.settings.get("local_storage_path", "") or "").strip() or "static"
    min_local_gb = float(config.settings.get("local_min_free_gb", 1.0) or 0.0)
    ok_pri, free_pri, reason_pri = config._check_dir_writable_and_space(pri_raw, min_local_gb)
    tiers_report.append({
        "tier": f"💾 Ổ Cứng Cục Bộ Chính ({os.path.abspath(pri_raw)})",
        "status": "ready" if ok_pri else "full",
        "detail": f"✅ Sẵn sàng (Còn trống {free_pri} GB)" if ok_pri else f"⚠️ Không đủ chỗ / Lỗi ({reason_pri}) -> Sẽ tự động chuyển sang Ổ cứng dự phòng!"
    })

    # 3. Kiểm tra Ổ cứng cục bộ Dự phòng (nếu có cấu hình)
    bak_raw = str(config.settings.get("local_backup_storage_path", "") or "").strip()
    if bak_raw:
        ok_bak, free_bak, reason_bak = config._check_dir_writable_and_space(bak_raw, 0.05)
        tiers_report.append({
            "tier": f"💽 Ổ Cứng Cục Bộ Dự Phòng ({os.path.abspath(bak_raw)})",
            "status": "ready" if ok_bak else "error",
            "detail": f"✅ Sẵn sàng tiếp nhận khi ổ chính đầy (Còn trống {free_bak} GB)" if ok_bak else f"❌ Lỗi ổ dự phòng: {reason_bak}"
        })

    return {
        "tiers": tiers_report,
        "active_local_dir": os.path.abspath(config.get_storage_base_dir())
    }


def backup_database_to_gdrive(force: bool = False) -> tuple:
    """
    Sao lưu cơ sở dữ liệu khuôn mặt & sự kiện (`faces.db`) lên chuỗi Google Drive (Chính -> Dự phòng -> Ổ cứng).
    """
    now = time.time()
    if not force and (now - gdrive_runtime_status["last_db_backup_ts"] < 6 * 3600):
        return False, "", "Chưa đến chu kỳ sao lưu CSDL định kỳ."

    if not os.path.exists("faces.db"):
        return False, "", "Không tìm thấy tệp cơ sở dữ liệu faces.db!"

    date_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    custom_name = f"faces_backup_{date_tag}.db"
    ok, file_url, msg = upload_file_to_gdrive("faces.db", subfolder="Database_Backup", custom_filename=custom_name)
    if ok:
        with _gdrive_lock:
            gdrive_runtime_status["last_db_backup_ts"] = now
        SystemStatus.add_log("☁️ Google Drive: Đã sao lưu dự phòng cơ sở dữ liệu (faces.db) lên đám mây.", "success")
    return ok, file_url, msg


def sync_recordings_to_gdrive() -> int:
    """
    Đồng bộ các tệp ghi hình liên tục hoàn tất trong thư mục recordings lên chuỗi Google Drive.
    """
    if not config.settings.get("gdrive_enabled", False) or not config.settings.get("gdrive_sync_recordings", False):
        return 0

    recordings_dir = config.get_recordings_storage_dir()
    if not os.path.exists(recordings_dir):
        return 0

    uploaded_count = 0
    now = time.time()
    for fname in os.listdir(recordings_dir):
        if not (fname.endswith(".mp4") or fname.endswith(".avi")):
            continue
        if fname in _synced_recordings:
            continue
        fpath = os.path.join(recordings_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if now - os.path.getmtime(fpath) < 60:
            continue

        ok, _, _ = upload_file_to_gdrive(fpath, subfolder="Recordings")
        if ok:
            _synced_recordings.add(fname)
            uploaded_count += 1

    return uploaded_count


def perform_gdrive_periodic_tasks():
    """
    Thực thi định kỳ từ luồng `app/cleanup.py`:
    1. Tự động xóa các tệp trên chuỗi Google Drive đã vượt quá số ngày lưu trữ (`gdrive_retention_days`).
    2. Tự động sao lưu dự phòng cơ sở dữ liệu `faces.db`.
    3. Tự động đẩy các video ghi hình liên tục.
    """
    if not config.settings.get("gdrive_enabled", False):
        return
    if not get_all_drive_targets():
        return

    if config.settings.get("gdrive_auto_cleanup", True):
        retention_days = int(config.settings.get("gdrive_retention_days", 30))
        cleanup_gdrive_expired_files(retention_days)

    if config.settings.get("gdrive_sync_db", True):
        backup_database_to_gdrive(force=False)

    if config.settings.get("gdrive_sync_recordings", False):
        sync_recordings_to_gdrive()
