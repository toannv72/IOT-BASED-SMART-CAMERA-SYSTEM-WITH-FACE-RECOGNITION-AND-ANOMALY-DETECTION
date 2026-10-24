@echo off
chcp 65001 >nul
title CAI DAT TU KHOI DONG CUNG WINDOWS
color 0A

echo ======================================================================
echo    CÀI ĐẶT TỰ ĐỘNG CHẠY SMART CAMERA KHI BẬT MÁY / CÓ ĐIỆN (WINDOWS)
echo ======================================================================
echo.

set "TARGET_BAT=%~dp0CHAY_1_NUT.bat"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SmartCamera_Startup.lnk"
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"

echo [*] File chuong trinh: %TARGET_BAT%
echo [*] Thu muc Startup: %SHORTCUT_PATH%
echo.

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%TARGET_BAT%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS_SCRIPT%"
echo oLink.Description = "Tu dong chay Smart Camera AI khi mo may" >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

cscript /nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%" >nul 2>&1

if exist "%SHORTCUT_PATH%" (
    echo ======================================================================
    echo  [THANH CONG] Đã cài đặt tự khởi động thành công!
    echo.
    echo  Tu nay, moi khi may tinh bat len hoac khi mat dien roi co dien lai:
    echo  -> He thong Smart Camera se TU DONG CHAY ma khong can ban phai mo!
    echo ======================================================================
) else (
    echo [LOI] Khong the tao shortcut trong thu muc Startup.
)

echo.
pause
