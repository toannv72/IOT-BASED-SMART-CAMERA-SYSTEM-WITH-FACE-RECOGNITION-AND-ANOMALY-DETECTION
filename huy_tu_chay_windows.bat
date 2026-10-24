@echo off
chcp 65001 >nul
title HUY TU KHOI DONG WINDOWS
color 0C

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SmartCamera_Startup.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [THANH CONG] Da huy tu khoi dong Smart Camera cung Windows!
) else (
    echo [THONG BAO] Smart Camera chua duoc cai tu khoi dong cung Windows.
)

echo.
pause
