import os
import time
import threading
from datetime import datetime, timedelta
import app.config as config
from app.database import SessionLocal, SystemEventLog

def get_folder_size(folder_path):
    """Tính tổng dung lượng thư mục bằng bytes"""
    total_size = 0
    if not os.path.exists(folder_path):
        return 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size

def perform_cleanup():
    """Thực hiện dọn dẹp log và tệp tin ảnh chụp cảnh báo cũ"""
    # Đọc cấu hình trực tiếp từ config.settings
    auto_cleanup_enabled = config.settings.get("auto_cleanup_enabled", False)
    if not auto_cleanup_enabled:
        return
        
    cleanup_older_than_days = config.settings.get("cleanup_older_than_days", 7)
    cleanup_max_size_gb = config.settings.get("cleanup_max_size_gb", 2.0)
    
    print(f"[CLEANUP] Bắt đầu quét dọn dẹp. Cấu hình: ngày tối đa={cleanup_older_than_days}, dung lượng tối đa={cleanup_max_size_gb} GB")
    
    db = SessionLocal()
    try:
        # 1. Dọn dẹp theo thời gian (Số ngày tối đa lưu trữ)
        cutoff_date = datetime.now() - timedelta(days=cleanup_older_than_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Lấy danh sách sự kiện cũ hơn ngày cấu hình
        old_events = db.query(SystemEventLog).filter(SystemEventLog.timestamp < cutoff_str).all()
        deleted_db_count = 0
        deleted_file_count = 0
        
        for event in old_events:
            # Xóa ảnh
            if event.image_path:
                local_path = event.image_path.lstrip('/')
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        deleted_file_count += 1
                    except Exception as e:
                        print(f"[CLEANUP] Không thể xóa tệp ảnh {local_path}: {e}")
            
            # Xóa video
            if event.video_path:
                local_path = event.video_path.lstrip('/')
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        deleted_file_count += 1
                    except Exception as e:
                        print(f"[CLEANUP] Không thể xóa tệp video {local_path}: {e}")
                        
            db.delete(event)
            deleted_db_count += 1
            
        if deleted_db_count > 0:
            db.commit()
            print(f"[CLEANUP] Đã xóa {deleted_db_count} bản ghi sự kiện và {deleted_file_count} tệp tin cũ hơn {cleanup_older_than_days} ngày.")
            from app.config import SystemStatus
            SystemStatus.add_log(f"🧹 Tự động dọn dẹp: Đã xóa {deleted_db_count} sự kiện cũ (> {cleanup_older_than_days} ngày).", "info")
            
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Lỗi khi xóa bản ghi cũ: {e}")
    finally:
        db.close()
        
    # 2. Dọn dẹp theo dung lượng tối đa (cleanup_max_size_gb)
    alerts_dir = os.path.join("static", "alerts")
    max_bytes = cleanup_max_size_gb * 1024 * 1024 * 1024
    
    if os.path.exists(alerts_dir):
        try:
            current_size = get_folder_size(alerts_dir)
            if current_size > max_bytes:
                print(f"[CLEANUP] Dung lượng hiện tại ({current_size / (1024**3):.4f} GB) vượt quá dung lượng tối đa ({cleanup_max_size_gb} GB). Tiến hành dọn dẹp.")
                
                # Quét tất cả file và sắp xếp theo thời gian sửa đổi (cũ nhất đứng trước)
                files_with_time = []
                for f in os.listdir(alerts_dir):
                    fp = os.path.join(alerts_dir, f)
                    if os.path.isfile(fp):
                        files_with_time.append((fp, os.path.getmtime(fp), os.path.getsize(fp)))
                        
                files_with_time.sort(key=lambda x: x[1])
                
                db = SessionLocal()
                deleted_capacity_files = 0
                try:
                    for fp, mtime, size in files_with_time:
                        if current_size <= max_bytes:
                            break
                            
                        # Đổi đường dẫn tệp cục bộ sang đường dẫn web để xóa trong DB
                        web_path = "/" + fp.replace("\\", "/")
                        event = db.query(SystemEventLog).filter(
                            (SystemEventLog.image_path == web_path) | (SystemEventLog.video_path == web_path)
                        ).first()
                        
                        if event:
                            db.delete(event)
                            
                        try:
                            os.remove(fp)
                            current_size -= size
                            deleted_capacity_files += 1
                        except Exception as e:
                            print(f"[CLEANUP] Không thể xóa tệp {fp}: {e}")
                            
                    db.commit()
                    if deleted_capacity_files > 0:
                        print(f"[CLEANUP] Đã giải phóng bộ nhớ: Xóa {deleted_capacity_files} tệp tin cũ nhất.")
                        from app.config import SystemStatus
                        SystemStatus.add_log(f"🧹 Tự động dọn dẹp: Đã xóa {deleted_capacity_files} tệp tin cũ nhất do vượt dung lượng tối đa.", "info")
                except Exception as e:
                    db.rollback()
                    print(f"[CLEANUP] Lỗi dọn dẹp dung lượng: {e}")
                finally:
                    db.close()
        except Exception as e:
            print(f"[CLEANUP] Lỗi quét thư mục alerts: {e}")

def cleanup_loop():
    """Vòng lặp chạy ngầm thực hiện dọn dẹp định kỳ"""
    print("[CLEANUP] Đã khởi chạy tiến trình dọn dẹp tự động chạy ngầm.")
    # Đợi 10 giây sau khi khởi động hệ thống rồi chạy lần đầu tiên
    time.sleep(10)
    while True:
        try:
            perform_cleanup()
        except Exception as e:
            print(f"[CLEANUP] Lỗi trong luồng chạy ngầm: {e}")
        # Chạy lại sau mỗi 5 phút (300 giây)
        time.sleep(300)

def start_cleanup_thread():
    """Khởi chạy luồng dọn dẹp ngầm"""
    t = threading.Thread(target=cleanup_loop, daemon=True, name="SystemCleanupThread")
    t.start()
