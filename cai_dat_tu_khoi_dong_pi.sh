#!/bin/bash
# ==============================================================================
# HỆ THỐNG SMART CAMERA EDGE AI - CÀI ĐẶT TỰ ĐỘNG KHỞI CHẠY TRÊN RASPBERRY PI 4
# Tự động chạy lại ngay khi cắm nguồn hoặc khi mất điện rồi có điện trở lại!
# ==============================================================================

# Màu sắc thông báo
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}   CÀI ĐẶT DỊCH VỤ TỰ ĐỘNG CHẠY SMART CAMERA (SYSTEMD DAEMON)         ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Kiểm tra quyền root / sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[LỖI] Vui lòng chạy script này với quyền sudo:${NC}"
    echo -e "       sudo bash cai_dat_tu_khoi_dong_pi.sh"
    exit 1
fi

# Lấy User thực tế đang đăng nhập (không phải root)
REAL_USER=${SUDO_USER:-$USER}
if [ "$REAL_USER" = "root" ]; then
    # Thử lấy user của thư mục cha
    REAL_USER=$(stat -c '%U' .)
fi

# Xác định thư mục dự án hiện tại
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo -e "${GREEN}[*] Thư mục dự án:${NC} $PROJECT_DIR"
echo -e "${GREEN}[*] Người dùng thực thi:${NC} $REAL_USER"

# Xác định file thực thi Python
if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
    echo -e "${GREEN}[*] Phát hiện môi trường ảo:${NC} $PYTHON_BIN"
elif [ -f "$PROJECT_DIR/venv/bin/python3" ]; then
    PYTHON_BIN="$PROJECT_DIR/venv/bin/python3"
    echo -e "${GREEN}[*] Phát hiện môi trường ảo:${NC} $PYTHON_BIN"
else
    PYTHON_BIN=$(which python3)
    echo -e "${YELLOW}[!] Không thấy thư mục venv, dùng Python hệ thống:${NC} $PYTHON_BIN"
fi

SERVICE_FILE="/etc/systemd/system/smartcamera.service"

echo -e "\n[*] Đang tạo tệp dịch vụ Systemd tại: $SERVICE_FILE..."

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=MSE Smart Camera AI Edge Surveillance System
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$PROJECT_DIR
Environment=OPENBLAS_CORETYPE=ARMV8
Environment=PYTHONUNBUFFERED=1
# Giải phóng cổng 8000 nếu đang bị chiếm dụng trước khi khởi chạy
ExecStartPre=/bin/bash -c "/usr/bin/fuser -k 8000/tcp 2>/dev/null || true"
# Đường dẫn khởi chạy hệ thống
ExecStart=$PYTHON_BIN main.py
# Tự động khởi động lại sau 5 giây nếu gặp sự cố hoặc camera bị gián đoạn
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"

echo -e "[*] Đang nạp cấu hình dịch vụ vào Systemd (daemon-reload)..."
systemctl daemon-reload

echo -e "[*] Đang kích hoạt tự động chạy khi khởi động bo mạch (systemctl enable)..."
systemctl enable smartcamera.service

echo -e "[*] Đang khởi động dịch vụ Smart Camera ngay bây giờ..."
systemctl restart smartcamera.service

sleep 2

# Kiểm tra trạng thái dịch vụ
if systemctl is-active --quiet smartcamera.service; then
    IP_LOCAL=$(hostname -I | awk '{print $1}')
    echo -e "\n${GREEN}======================================================================${NC}"
    echo -e "${GREEN}  [THÀNH CÔNG] ĐÃ KÍCH HOẠT DỊCH VỤ TỰ ĐỘNG CHẠY THÀNH CÔNG!          ${NC}"
    echo -e "${GREEN}======================================================================${NC}"
    echo -e "Từ nay:"
    echo -e " 1. Khi ${YELLOW}mất điện rồi có điện lại${NC}, Raspberry Pi sẽ tự bật nguồn và hệ thống"
    echo -e "    Smart Camera sẽ ${GREEN}TỰ ĐỘNG CHẠY NGAY LẬP TỨC${NC} (sau ~15-20s boot)."
    echo -e " 2. Không cần phải cắm màn hình, bàn phím, hay đăng nhập SSH gõ lệnh thủ công."
    echo -e " 3. Nếu gặp sự cố, hệ thống sẽ ${GREEN}tự động hồi phục sau 5 giây${NC}."
    echo -e "\n${BLUE}👉 Địa chỉ truy cập Web Dashboard:${NC}"
    echo -e "   - Trên Pi:       http://localhost:8000"
    if [ -n "$IP_LOCAL" ]; then
        echo -e "   - Từ máy khác:   http://$IP_LOCAL:8000"
    fi
    echo -e "\n${YELLOW}Các lệnh hữu ích quản lý hệ thống:${NC}"
    echo -e "   - Xem nhật ký hoạt động (Real-time logs):  ${GREEN}journalctl -u smartcamera.service -f${NC}"
    echo -e "   - Kiểm tra trạng thái:                     ${GREEN}sudo systemctl status smartcamera.service${NC}"
    echo -e "   - Khởi động lại:                           ${GREEN}sudo systemctl restart smartcamera.service${NC}"
    echo -e "   - Dừng hệ thống:                           ${GREEN}sudo systemctl stop smartcamera.service${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
else
    echo -e "\n${RED}[CẢNH BÁO] Dịch vụ đã được kích hoạt nhưng chưa ở trạng thái active.${NC}"
    echo -e "Kiểm tra lỗi chi tiết bằng lệnh: ${YELLOW}journalctl -u smartcamera.service -n 30 --no-pager${NC}"
fi
