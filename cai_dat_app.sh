#!/bin/bash
# ==============================================================================
# HỆ THỐNG SMART CAMERA EDGE AI - TRÌNH CÀI ĐẶT ỨNG DỤNG TỰ ĐỘNG KHỞI ĐỘNG
# Chạy 1 lần duy nhất: Ứng dụng tự cài đặt và tự khởi động mỗi khi bật máy/có điện!
# ==============================================================================

# Định dạng màu sắc terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}======================================================================${NC}"
echo -e "${BOLD}${CYAN}   TRÌNH CÀI ĐẶT ỨNG DỤNG SMART CAMERA AI - TỰ KHỞI ĐỘNG HỆ THỐNG    ${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e " Mục tiêu: Cài đặt hệ thống thành một ${GREEN}Ứng dụng nền (Background App)${NC}"
echo -e "           Mỗi khi ${YELLOW}mở máy${NC} hoặc ${YELLOW}mất điện có điện lại${NC} là tự động chạy 100%!"
echo -e "${CYAN}----------------------------------------------------------------------${NC}\n"

# 1. Xác định thư mục dự án và Người dùng thực tế
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$PROJECT_DIR"

if [ -n "$SUDO_USER" ]; then
    CURRENT_USER="$SUDO_USER"
else
    CURRENT_USER="$USER"
fi
USER_HOME=$(eval echo "~$CURRENT_USER")

echo -e "${GREEN}[1/6] Nhận diện môi trường hệ thống:${NC}"
echo -e "      - Thư mục dự án: ${CYAN}$PROJECT_DIR${NC}"
echo -e "      - Người dùng sở hữu: ${CYAN}$CURRENT_USER${NC}"
echo -e "      - Thư mục cá nhân: ${CYAN}$USER_HOME${NC}\n"

# 2. Khởi tạo thư mục tạm và Môi trường ảo Python (Venv)
echo -e "${GREEN}[2/6] Kiểm tra môi trường ảo Python (Venv)...${NC}"
mkdir -p "$PROJECT_DIR/tmp"

if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "      [*] Đang tạo môi trường ảo Python venv..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
PIP_BIN="$PROJECT_DIR/venv/bin/pip"

# 3. Cài đặt thư viện dependencies tối ưu cho Raspberry Pi (tránh lỗi /tmp đầy)
echo -e "\n${GREEN}[3/6] Kiểm tra các thư viện AI và hệ thống...${NC}"
need_install=false

if ! "$PYTHON_BIN" -c "import torch, cv2, fastapi, ultralytics" 2>/dev/null; then
    need_install=true
fi

if [ "$need_install" = true ]; then
    echo -e "      [*] Đang cài đặt thư viện cần thiết từ requirements.txt..."
    TMPDIR="$PROJECT_DIR/tmp" "$PIP_BIN" install --no-cache-dir -r requirements.txt
    
    echo -e "      [*] Đang cấu hình PyTorch tối ưu CPU ARMv8 (chống lỗi Illegal instruction)..."
    TMPDIR="$PROJECT_DIR/tmp" "$PIP_BIN" install --no-cache-dir --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cpu
else
    echo -e "      [OK] Các thư viện AI đã được cài đặt đầy đủ."
fi

# 4. Tự động kiểm tra và cấu hình Camera về 0 nếu cần
echo -e "\n${GREEN}[4/6] Chuẩn hóa tệp cấu hình camera...${NC}"
if [ -f "cameras_config.json" ]; then
    # Đảm bảo camera USB mặc định là source 0 nếu chưa chỉnh
    sed -i 's/"source": "1"/"source": "0"/g' cameras_config.json 2>/dev/null || true
    echo -e "      [OK] Đã cấu hình nguồn camera mặc định."
fi

# 5. Đăng ký dịch vụ tự khởi động cùng hệ thống (Systemd Daemon Service)
echo -e "\n${GREEN}[5/6] Đăng ký ứng dụng tự động khởi chạy khi bật máy (Systemd Service)...${NC}"
SERVICE_FILE="/etc/systemd/system/smartcamera.service"

SERVICE_CONTENT="[Unit]
Description=MSE Smart Camera AI Edge Surveillance System
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=OPENBLAS_CORETYPE=ARMV8
Environment=PYTHONUNBUFFERED=1
# Giải phóng cổng 8000 nếu đang bị chiếm dụng
ExecStartPre=/bin/bash -c \"/usr/bin/fuser -k 8000/tcp 2>/dev/null || true\"
# Lệnh khởi chạy hệ thống chính
ExecStart=$PYTHON_BIN main.py
# Tự động khởi động lại sau 5 giây nếu gặp sự cố
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"

# Nếu chạy với quyền sudo hoặc dùng sudo để ghi service
if [ "$EUID" -eq 0 ]; then
    echo "$SERVICE_CONTENT" > "$SERVICE_FILE"
    chmod 644 "$SERVICE_FILE"
    systemctl daemon-reload
    systemctl enable smartcamera.service
    systemctl restart smartcamera.service
else
    echo "$SERVICE_CONTENT" | sudo tee "$SERVICE_FILE" > /dev/null
    sudo chmod 644 "$SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl enable smartcamera.service
    sudo systemctl restart smartcamera.service
fi
echo -e "      [OK] Đã kích hoạt dịch vụ tự khởi động: ${CYAN}smartcamera.service${NC}"

# 6. Tạo biểu tượng ứng dụng trên màn hình Desktop (Desktop App Shortcut)
echo -e "\n${GREEN}[6/6] Tạo biểu tượng ứng dụng trên màn hình Desktop...${NC}"
DESKTOP_DIR="$USER_HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    DESKTOP_FILE="$DESKTOP_DIR/SmartCamera.desktop"
    cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart Camera AI
Comment=Hệ thống giám sát an ninh thông minh AI
Exec=xdg-open http://localhost:8000
Icon=camera-web
Terminal=false
StartupNotify=true
Categories=Utility;AudioVideo;
EOF
    chmod +x "$DESKTOP_FILE"
    chown "$CURRENT_USER:$CURRENT_USER" "$DESKTOP_FILE" 2>/dev/null || true
    echo -e "      [OK] Đã tạo biểu tượng app tại: ${CYAN}$DESKTOP_FILE${NC}"
fi

# Hoàn thành và in kết quả
sleep 2
IP_LAN=$(hostname -I 2>/dev/null | awk '{print $1}')
echo -e "\n${CYAN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}   CÀI ĐẶT THÀNH CÔNG! HỆ THỐNG ĐÃ TRỞ THÀNH ỨNG DỤNG TỰ CHẠY         ${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e " ${BOLD}ĐẶC ĐIỂM HOẠT ĐỘNG TỰ ĐỘNG:${NC}"
echo -e " ✔ ${GREEN}Tự khởi động:${NC} Mỗi lần mở máy hoặc cắm điện lại -> Ứng dụng tự chạy sau ~15s."
echo -e " ✔ ${GREEN}Không cần thao tác:${NC} Không cần mở terminal gõ lệnh, không cần cắm màn hình."
echo -e " ✔ ${GREEN}Tự hồi phục:${NC} Nếu có sự cố camera hoặc lỗi tiến trình, hệ thống tự reset sau 5s."
echo -e " ✔ ${GREEN}Icon màn hình:${NC} Có biểu tượng 'Smart Camera AI' ngay trên Desktop của Pi."
echo -e ""
echo -e " ${BOLD}ĐỊA CHỈ TRUY CẬP WEB DASHBOARD:${NC}"
echo -e " 👉 Trên máy này:         ${CYAN}http://localhost:8000${NC}"
if [ -n "$IP_LAN" ]; then
    echo -e " 👉 Điện thoại/Máy khác:  ${CYAN}http://$IP_LAN:8000${NC}"
fi
echo -e ""
echo -e " ${BOLD}CÁC LỆNH TIỆN ÍCH:${NC}"
echo -e " • Xem trực tiếp camera hoạt động (Log):  ${YELLOW}sudo journalctl -u smartcamera -f${NC}"
echo -e " • Kiểm tra trạng thái ứng dụng:          ${YELLOW}sudo systemctl status smartcamera${NC}"
echo -e " • Tạm dừng ứng dụng:                     ${YELLOW}sudo systemctl stop smartcamera${NC}"
echo -e " • Gỡ bỏ chế độ tự chạy:                  ${YELLOW}bash go_cai_dat_app.sh${NC}"
echo -e "${CYAN}======================================================================${NC}\n"
