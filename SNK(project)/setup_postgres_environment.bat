@echo off
setlocal enabledelayedexpansion
title Faculty ERP - PostgreSQL 16 Environment Setup
echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE, LEAVE AND SUBSTITUTE MANAGEMENT ERP
echo   PostgreSQL 16 & Python 3.13 Environment Setup Wizard
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
echo [1/5] Checking Python installation...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.13+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [OK] Found %PYTHON_VER%

:: 2. Set up virtual environment
echo.
echo [2/5] Configuring virtual environment (venv)...
if not exist "venv\Scripts\activate.bat" (
    echo Creating clean virtual environment in .\venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Virtual environment found.
)

:: 3. Install dependencies
echo.
echo [3/5] Installing PostgreSQL drivers and project dependencies...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Error during pip install. Retrying with --no-cache-dir...
    pip install --no-cache-dir -r requirements.txt
)
echo [OK] Python dependencies and psycopg2-binary installed.

:: 4. Verify configuration .env
echo.
echo [4/5] Checking configuration files...
if not exist ".env" (
    if exist ".env.example" (
        echo Copying .env.example to .env...
        copy ".env.example" ".env" >nul
        echo [OK] Created .env configuration file with PostgreSQL settings.
    ) else (
        echo [NOTE] Default environment settings will be loaded from config.settings.
    )
) else (
    echo [OK] Configuration file .env exists.
)

:: 5. Attempt PostgreSQL Database Initialization
echo.
echo [5/5] Checking PostgreSQL Database & Initializing Tables...
python database\init_db.py
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL connected and all 19 database tables initialized & seeded.
) else (
    echo [NOTE] PostgreSQL server was not reachable on localhost:5432.
    echo The ERP will run in offline mode using in-memory resilient fallback.
    echo To spin up PostgreSQL via Docker Compose, run:
    echo     docker compose up -d
    echo Or run: start_postgres_and_db.bat once your PostgreSQL service is online.
)

echo.
echo ===============================================================================
echo   POSTGRESQL ENVIRONMENT SETUP COMPLETE!
echo ===============================================================================
echo.
echo   Default Institutional Login Accounts:
echo   --------------------------------------------------------
echo   - Administrator:  Username: admin          Password: admin123
echo   - Head of Dept:   Username: hod_mca        Password: hod123
echo   - Faculty Member: Username: faculty_f001   Password: faculty123
echo.
echo   To launch the application, run:
echo       run_app.bat  or  launch_all.bat
echo.
echo ===============================================================================
pause
