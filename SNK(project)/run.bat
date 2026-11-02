@echo off
setlocal EnableExtensions
title AI-Enabled Faculty Attendance ERP - Kiosk Terminal & Desktop Launch
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" goto :run_py
call "venv\Scripts\activate.bat"

:run_py
python main.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] Application exited with code %ERRORLEVEL%.
    pause
)
