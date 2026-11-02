@echo off
title AI-Enabled Faculty Attendance, Leave and Substitute Management ERP
echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE, LEAVE AND SUBSTITUTE MANAGEMENT ERP
echo   Production Release v1.0.0
echo ===============================================================================
echo.

cd /d "%~dp0"

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Running initial setup wizard...
    call setup_environment.bat
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Setup failed.
        pause
        exit /b 1
    )
)

:: Check PostgreSQL Service Status on Port 5432
netstat -ano | findstr /R ":5432.*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL service detected running on port 5432.
) else (
    echo [INFO] PostgreSQL on port 5432 not detected running as a service.
    echo        If PostgreSQL is stopped, start it via Services or: docker compose up -d
    echo        The ERP will seamlessly use in-memory resilient fallback if offline.
)

echo [OK] Launching Faculty ERP Desktop Application...
echo.
call "venv\Scripts\activate.bat"
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] Application exited with code %ERRORLEVEL%.
    pause
)
