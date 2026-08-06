import os
import time
import json
import threading
import psutil
from datetime import datetime

class TelemetryTracker:
    # Kho lưu trữ các mẫu đo lường (running samples)
    _lock = threading.Lock()
    _start_time = time.time()
    
    # Latencies in seconds
    _face_detection_samples = []
    _face_recognition_samples = []
    _yolo_fire_samples = []
    _yolo_fall_samples = []
    _yolo_intrusion_samples = []
    _telegram_latency_samples = []
    
    # Camera frame times
    _camera_frame_times = {} # camera_id: [samples]
    
    # Stream freeze detection (max frame interval in seconds during alerts)
    _max_freeze_during_alert = 0.0
    
    @classmethod
    def record_face_detection(cls, duration):
        with cls._lock:
            cls._face_detection_samples.append(duration)
            if len(cls._face_detection_samples) > 50:
                cls._face_detection_samples.pop(0)
                
    @classmethod
    def record_face_recognition(cls, duration):
        with cls._lock:
            cls._face_recognition_samples.append(duration)
            if len(cls._face_recognition_samples) > 50:
                cls._face_recognition_samples.pop(0)

    @classmethod
    def record_yolo_fire(cls, duration):
        with cls._lock:
            cls._yolo_fire_samples.append(duration)
            if len(cls._yolo_fire_samples) > 50:
                cls._yolo_fire_samples.pop(0)

    @classmethod
    def record_yolo_fall(cls, duration):
        with cls._lock:
            cls._yolo_fall_samples.append(duration)
            if len(cls._yolo_fall_samples) > 50:
                cls._yolo_fall_samples.pop(0)

    @classmethod
    def record_yolo_intrusion(cls, duration):
        with cls._lock:
            cls._yolo_intrusion_samples.append(duration)
            if len(cls._yolo_intrusion_samples) > 50:
                cls._yolo_intrusion_samples.pop(0)

    @classmethod
    def record_telegram_latency(cls, duration):
        with cls._lock:
            cls._telegram_latency_samples.append(duration)
            if len(cls._telegram_latency_samples) > 10:
                cls._telegram_latency_samples.pop(0)

    @classmethod
    def record_frame_time(cls, camera_id, duration):
        with cls._lock:
            if camera_id not in cls._camera_frame_times:
                cls._camera_frame_times[camera_id] = []
            cls._camera_frame_times[camera_id].append(duration)
            if len(cls._camera_frame_times[camera_id]) > 50:
                cls._camera_frame_times[camera_id].pop(0)
            
            # Nếu đang có gửi cảnh báo và thời gian xử lý khung hình tăng đột biến, ghi nhận độ đóng băng
            if duration > 0.2:
                if duration > cls._max_freeze_during_alert:
                    cls._max_freeze_during_alert = duration

    @classmethod
    def get_average(cls, samples, factor=1000.0, default=0.0):
        if not samples:
            return default
        return round((sum(samples) / len(samples)) * factor, 2)

    @classmethod
    def generate_report(cls):
        with cls._lock:
            # Lấy thông tin tài nguyên hệ thống
            process = psutil.Process(os.getpid())
            cpu_usage = round(psutil.cpu_percent(interval=None), 1)
            memory_info = process.memory_info()
            memory_rss_mb = round(memory_info.rss / (1024 * 1024), 1)
            
            # Tính toán FPS trung bình của từng camera dựa trên mẫu frame time
            camera_fps = {}
            for cam_id, samples in cls._camera_frame_times.items():
                if samples:
                    avg_frame_time = sum(samples) / len(samples)
                    camera_fps[cam_id] = round(1.0 / (avg_frame_time + 1e-6), 1)
            
            report = {
                "thoi_gian_cap_nhat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "thoi_gian_da_chay_giay": round(time.time() - cls._start_time, 1),
                "tai_nguyen_he_thong": {
                    "cpu_su_dung_phantram": cpu_usage,
                    "ram_su_dung_mb": memory_rss_mb
                },
                "hieu_nang_camera_fps": camera_fps,
                "do_tre_suy_luan_ai_ms": {
                    "phat_hien_khuon_mat_mtcnn_ms": cls.get_average(cls._face_detection_samples),
                    "nhan_dien_dac_trung_facenet_ms": cls.get_average(cls._face_recognition_samples),
                    "phat_hien_chay_yolo_ms": cls.get_average(cls._yolo_fire_samples),
                    "phat_hien_nga_yolo_ms": cls.get_average(cls._yolo_fall_samples),
                    "phat_hien_xam_nhap_yolo_ms": cls.get_average(cls._yolo_intrusion_samples)
                },
                "do_tre_truyen_thong_canh_bao": {
                    "thoi_gian_gui_telegram_giay": cls.get_average(cls._telegram_latency_samples, factor=1.0, default=0.0),
                    "dong_bang_luong_video_max_ms": round(cls._max_freeze_during_alert * 1000.0, 1)
                }
            }
            return report

def _telemetry_writer_loop():
    while True:
        try:
            report = TelemetryTracker.generate_report()
            with open("ket_qua_do_luong.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[TELEMETRY] [ERROR] Không thể ghi file kết quả đo lường: {e}")
        time.sleep(5.0)

def start_telemetry_monitoring():
    t = threading.Thread(target=_telemetry_writer_loop, daemon=True, name="TelemetryWriter")
    t.start()
    print("[TELEMETRY] Luồng tự động ghi nhận kết quả đo lường thực tế đã được kích hoạt.")
