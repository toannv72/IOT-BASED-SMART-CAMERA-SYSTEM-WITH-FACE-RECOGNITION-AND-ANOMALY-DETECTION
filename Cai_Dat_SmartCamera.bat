@echo off
cd /d "%~dp0"
python cai_dat_app_windows.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the chay script cai dat. Vui long kiem tra Python tren may.
    pause
)
