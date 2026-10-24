@echo off
cd /d "%~dp0"
python chay_nhanh.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the khoi chay he thong. Vui long kiem tra Python tren may.
    pause
)
