@echo off
cls
echo ========================================
echo   Clinic Management System - Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first with: python -m venv venv
    echo.
    pause
    exit /b 1
)

echo [1/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo       Virtual environment activated!
echo.

echo [2/4] Checking Django installation...
python -c "import django" 2>nul
if errorlevel 1 (
    echo ERROR: Django not installed in virtual environment
    echo Please install dependencies first: pip install -r requirements.txt
    pause
    exit /b 1
)
echo       Django is installed!
echo.

echo [3/4] Running database migrations...
python manage.py migrate --noinput
if errorlevel 1 (
    echo WARNING: Migration issues detected (continuing anyway)
)
echo       Migrations complete!
echo.

echo [4/4] Starting Django development server...
echo.
echo ========================================
echo   Server will start at:
echo   http://127.0.0.1:8000
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver

pause
