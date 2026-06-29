@echo off
title He Thong Giam Sat Thong Minh AI
:menu
cls
echo =======================================================
echo     HE THONG GIAM SAT AN NINH THONG MINH AI (YOLO + FaceNet)
echo =======================================================
echo.
echo [1] Cai dat cac thu vien (requirements.txt)
echo [2] Cai dat PyTorch ho tro GPU NVIDIA (CUDA 12.1)
echo [3] KHOI CHAY UNIFIED WEB DASHBOARD (Khuyen dung)
echo.
echo --- Cac phan he don le (Giao dien OpenCV cu) ---
echo [4] Chay API Server khuon mat (face_api.py)
echo [5] Dang ky khuon mat bang Webcam (register_face.py)
echo [6] Nhan dien khuon mat bang Webcam (face_camera.py)
echo [7] Canh bao sam nhap ROI YOLOv5 (test_video.py)
echo [8] Test phat hien nga YOLOv8 custom (test_fall_video.py)
echo [9] Test nhan dien chay no custom (verify_fire_stream.py)
echo [10] Thoat
echo.
echo =======================================================
set /p choice=Nhap lua chon cua ban (1-10): 

if "%choice%"=="1" goto install_req
if "%choice%"=="2" goto install_cuda
if "%choice%"=="3" goto run_web
if "%choice%"=="4" goto run_api
if "%choice%"=="5" goto reg_face
if "%choice%"=="6" goto face_cam
if "%choice%"=="7" goto roi
if "%choice%"=="8" goto test_fall
if "%choice%"=="9" goto test_fire
if "%choice%"=="10" goto exit
goto menu

:install_req
echo Dang cai dat requirements.txt...
pip install -r requirements.txt
pause
goto menu

:install_cuda
echo Dang cai dat PyTorch ho tro GPU CUDA...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pause
goto menu

:run_web
echo Dang khoi chay Unified Web Dashboard...
python main.py
pause
goto menu

:run_api
echo Dang chay face_api.py...
python face_api.py
pause
goto menu

:reg_face
echo Dang chay register_face.py...
python register_face.py
pause
goto menu

:face_cam
echo Dang chay face_camera.py...
python face_camera.py
pause
goto menu


:roi
echo Dang chay test_video.py...
python test_video.py
pause
goto menu

:test_fall
echo Dang chay test_fall_video.py...
python test_fall_video.py
pause
goto menu

:test_fire
echo Dang chay verify_fire_stream.py...
python verify_fire_stream.py
pause
goto menu

:exit
exit
