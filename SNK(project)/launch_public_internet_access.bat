@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title AI-Enabled Faculty Attendance ERP - Global Internet Access Gateway

echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE ERP - GLOBAL INTERNET ACCESS GATEWAY
echo   Generates Public HTTPS Links Accessible on ANY Computer / Phone Worldwide
echo ===============================================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" goto :no_venv
call "venv\Scripts\activate.bat"
goto :start_public

:no_venv
echo [ERROR] Virtual environment not found at venv\Scripts\activate.bat
echo Please run setup_environment.bat first to configure dependencies.
pause
exit /b 1

:start_public
echo [INFO] Initializing Public Internet Tunnel Gateway...
echo.
python services\public_tunnel_manager.py auto

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] Public gateway exited with code %ERRORLEVEL%.
    pause
)
