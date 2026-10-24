#!/bin/bash
# ==============================================================================
# SCRIPT KHỞI CHẠY SMART CAMERA BẰNG 1 CLICK TRÊN RASPBERRY PI
# ==============================================================================

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "      HỆ THỐNG SMART CAMERA EDGE AI - KHỞI CHẠY 1 NÚT (LINUX/PI)"
echo "======================================================================"

# Giải phóng cổng 8000 nếu đang bị chiếm
fuser -k 8000/tcp 2>/dev/null || true

# Tự động mở trình duyệt sau 3 giây
(sleep 3 && which xdg-open >/dev/null && xdg-open http://localhost:8000) &

# Chạy python trong venv nếu có
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python main.py
else
    python3 main.py
fi
