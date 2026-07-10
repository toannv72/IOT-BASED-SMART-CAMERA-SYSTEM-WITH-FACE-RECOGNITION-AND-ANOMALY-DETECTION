#!/bin/bash

# Script khởi chạy hệ thống trên Raspberry Pi 4 (Linux)
# Đảm bảo phân quyền chạy cho script: chmod +x chay_he_thong.sh

show_menu() {
    clear
    echo "======================================================="
    echo "    HỆ THỐNG GIÁM SÁT AN NINH THÔNG MINH AI (YOLO + FaceNet)"
    echo "                   TRÊN RASPBERRY PI 4"
    echo "======================================================="
    echo ""
    echo "[1] Cài đặt thư viện hệ thống (apt dependencies)"
    echo "[2] Khởi tạo Venv và cài đặt PyTorch CPU (ARM64)"
    echo "[3] KHỞI CHẠY UNIFIED WEB DASHBOARD (Khuyên dùng)"
    echo ""
    echo "--- Các phân hệ đơn lẻ (Giao diện OpenCV cũ) ---"
    echo "[4] Chạy API Server khuôn mặt (face_api.py)"
    echo "[5] Đăng ký khuôn mặt bằng Webcam (register_face.py)"
    echo "[6] Nhận diện khuôn mặt bằng Webcam (face_camera.py)"
    echo "[7] Cảnh báo xâm nhập ROI YOLOv5 (test_video.py)"
    echo "[8] Test phát hiện ngã YOLOv8 (test_fall_video.py)"
    echo "[9] Test nhận diện cháy nổ (verify_fire_stream.py)"
    echo "[10] Thoát"
    echo ""
    echo "======================================================="
    echo -n "Nhập lựa chọn của bạn (1-10): "
}

press_any_key() {
    echo ""
    echo -n "Nhấn phím bất kỳ để tiếp tục..."
    read -n 1
}

# Đảm bảo đang ở trong môi trường ảo khi chạy python
run_python() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        python "$@"
    else
        python3 "$@"
    fi
}

while true; do
    show_menu
    read choice
    case $choice in
        1)
            echo "Đang cài đặt thư viện hệ thống cần thiết cho OpenCV..."
            sudo apt update
            sudo apt install -y libglib2.0-0 libgl1-mesa-glx python3-venv python3-pip
            press_any_key
            ;;
        2)
            echo "Đang khởi tạo môi trường ảo và cài đặt PyTorch CPU..."
            if [ ! -d "venv" ]; then
                python3 -m venv venv
            fi
            source venv/bin/activate
            pip install --upgrade pip
            pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
            pip install -r requirements.txt
            press_any_key
            ;;
        3)
            echo "Đang khởi chạy Unified Web Dashboard..."
            run_python main.py
            press_any_key
            ;;
        4)
            echo "Đang chạy face_api.py..."
            run_python face_api.py
            press_any_key
            ;;
        5)
            echo "Đang chạy register_face.py..."
            run_python register_face.py
            press_any_key
            ;;
        6)
            echo "Đang chạy face_camera.py..."
            run_python face_camera.py
            press_any_key
            ;;
        7)
            echo "Đang chạy test_video.py..."
            run_python test_video.py
            press_any_key
            ;;
        8)
            echo "Đang chạy test_fall_video.py..."
            run_python test_fall_video.py
            press_any_key
            ;;
        9)
            echo "Đang chạy verify_fire_stream.py..."
            run_python verify_fire_stream.py
            press_any_key
            ;;
        10)
            echo "Thoát chương trình."
            exit 0
            ;;
        *)
            echo "Lựa chọn không hợp lệ!"
            sleep 1
            ;;
    esac
done
