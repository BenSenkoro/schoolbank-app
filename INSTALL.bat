@echo off
title Mbonea School Bank - Installation
color 1F
echo.
echo  ==========================================
echo   MBONEA SCHOOL BANK - First Time Setup
echo  ==========================================
echo.
echo  This will set up the system on this computer.
echo  Please wait, do not close this window...
echo.

cd /d "%~dp0"

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed on this computer.
    echo.
    echo  Please install Python first:
    echo  1. Open your browser
    echo  2. Go to: https://www.python.org/downloads/
    echo  3. Download and install Python
    echo  4. IMPORTANT: Tick "Add Python to PATH"
    echo  5. Then run this file again
    echo.
    pause
    exit
)

echo  Python found. Continuing setup...
echo.

:: Create virtual environment
echo  Setting up virtual environment...
python -m venv venv
echo  Done.
echo.

:: Activate and install packages
echo  Installing required packages...
call venv\Scripts\activate
pip install -r requirements.txt --quiet
echo  Done.
echo.

:: Run migrations
echo  Setting up database...
python manage.py migrate --run-syncdb
echo  Done.
echo.

:: Ask to create admin account
echo  ==========================================
echo   Create Admin Account
echo  ==========================================
echo.
echo  You need to create the main admin account.
echo  Please follow the prompts below:
echo.
python manage.py createsuperuser
echo.

:: Set role to admin (patch)
echo  Finalizing setup...
python manage.py shell -c "from accounts.models import CustomUser; u = CustomUser.objects.last(); u.role = 'admin'; u.save(); print('Admin role set for:', u.username)"
echo.

echo  ==========================================
echo   Installation Complete!
echo  ==========================================
echo.
echo  To start the system, double-click:
echo  start.pyw
echo.
echo  Or if that doesn't work, double-click:
echo  run.bat
echo.
pause