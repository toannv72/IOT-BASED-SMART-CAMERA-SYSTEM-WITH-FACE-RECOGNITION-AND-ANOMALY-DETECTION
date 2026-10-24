#!/bin/bash
# ==============================================================================
# HỦY TỰ ĐỘNG KHỞI ĐỘNG VÀ DỪNG DỊCH VỤ SMART CAMERA TRÊN RASPBERRY PI
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
    echo "[LỖI] Vui lòng chạy script này với quyền sudo: sudo bash tat_tu_khoi_dong_pi.sh"
    exit 1
fi

echo "[*] Đang dừng dịch vụ Smart Camera..."
systemctl stop smartcamera.service 2>/dev/null || true

echo "[*] Đang tắt chế độ tự khởi động cùng bo mạch..."
systemctl disable smartcamera.service 2>/dev/null || true

echo "[*] Đang gỡ bỏ tệp cấu hình service..."
rm -f /etc/systemd/system/smartcamera.service
systemctl daemon-reload

echo "======================================================================"
echo " [THÀNH CÔNG] Đã hủy dịch vụ tự khởi động Smart Camera trên Raspberry Pi!"
echo "======================================================================"
