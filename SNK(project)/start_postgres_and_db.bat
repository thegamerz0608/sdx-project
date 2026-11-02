@echo off
title Initialize Faculty ERP Database on PostgreSQL 16
echo ===============================================================================
echo   FACULTY ERP - POSTGRESQL 16 DATABASE INITIALIZATION & SEEDING
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Check PostgreSQL listening on port 5432
echo [1/3] Checking PostgreSQL service connectivity (port 5432)...
netstat -ano | findstr /R ":5432.*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL service is listening on port 5432.
) else (
    echo [NOTE] Port 5432 is not currently listening.
    echo If running via Docker Compose, spin up the container using:
    echo     docker compose up -d
    echo Or ensure the Windows PostgreSQL service is started.
    echo.
)

:: 2. Activate Python environment
echo [2/3] Checking Python virtual environment...
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [INFO] Running using system Python...
)

:: 3. Run database initialization and schema migration
echo.
echo [3/3] Running init_db.py to create schema and seed tables...
python database\init_db.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===============================================================================
    echo [SUCCESS] PostgreSQL Connected and All Tables Created & Seeded!
    echo ===============================================================================
    echo Database 'faculty_erp_db' is now live with all normalized tables and seed data.
    echo You can now launch the ERP application using:
    echo     run_app.bat  or  launch_all.bat
    echo ===============================================================================
) else (
    echo.
    echo [ERROR] PostgreSQL initialization encountered an issue.
    echo Check database credentials in .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD).
)

echo.
pause
