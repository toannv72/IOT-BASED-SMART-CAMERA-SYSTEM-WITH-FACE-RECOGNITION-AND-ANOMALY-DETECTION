@echo off
cd /d "%~dp0"
python -c "import os; a=os.environ.get('APPDATA',''); u=os.environ.get('USERPROFILE',''); s1=os.path.join(a,r'Microsoft\Windows\Start Menu\Programs\Startup\Smart Camera AI.lnk'); s2=os.path.join(u,r'Desktop\Smart Camera AI.lnk'); s3=os.path.join(a,r'Microsoft\Windows\Start Menu\Programs\Startup\SmartCamera_Startup.lnk'); [os.remove(p) for p in [s1,s2,s3] if os.path.exists(p)]; print('======================================================================'); print('[THANH CONG] Da go bo tu khoi dong Smart Camera va xoa bieu tuong Desktop!'); print('======================================================================')"
pause
