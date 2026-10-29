@echo off
title Mbonea School Bank
color 1F
echo.
echo  ==========================================
echo   MBONEA SCHOOL BANK - Starting Server...
echo  ==========================================
echo.
echo  Please wait while the system starts up.
echo  Do NOT close this window while the bank
echo  system is in use.
echo.
echo  Opening browser in 3 seconds...
echo.

cd /d "%~dp0"
call venv\Scripts\activate

start /b timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/login/

python manage.py runserver 127.0.0.1:8000 --noreload

echo.
echo  Server stopped. You can close this window.
pause