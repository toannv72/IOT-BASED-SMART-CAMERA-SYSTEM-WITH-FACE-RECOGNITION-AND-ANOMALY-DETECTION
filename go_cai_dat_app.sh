#!/bin/bash
# ==============================================================================
# GỠ CÀI ĐẶT ỨNG DỤNG TỰ KHỞI ĐỘNG SMART CAMERA TRÊN RASPBERRY PI
# ==============================================================================

echo "[*] Đang dừng dịch vụ Smart Camera..."
sudo systemctl stop smartcamera.service 2>/dev/null || true

echo "[*] Đang tắt tự khởi động cùng hệ thống..."
sudo systemctl disable smartcamera.service 2>/dev/null || true

echo "[*] Đang xóa tệp dịch vụ hệ thống..."
sudo rm -f /etc/systemd/system/smartcamera.service
sudo systemctl daemon-reload

echo "[*] Đang xóa biểu tượng ứng dụng trên màn hình Desktop..."
rm -f ~/Desktop/SmartCamera.desktop 2>/dev/null || true

echo "======================================================================"
echo " [THÀNH CÔNG] Đã gỡ bỏ ứng dụng tự khởi động Smart Camera thành công!"
echo "======================================================================"
