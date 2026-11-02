@echo off
title Pro Controller Gaming Server Launcher
echo ===================================================
echo   Starting Local PHP Server for SDX04 Project
echo ===================================================
echo.

cd /d "%~dp0"

SET PHP_PATH=D:\xampp\php\php.exe
IF NOT EXIST "%PHP_PATH%" SET PHP_PATH=C:\xampp\php\php.exe

IF EXIST "%PHP_PATH%" (
    echo [INFO] Found PHP at %PHP_PATH%
    echo [INFO] Server running at http://localhost:8000
    echo [INFO] Opening browser at http://localhost:8000 ...
    echo [INFO] Press Ctrl+C to stop the server.
    echo.
    start http://localhost:8000
    "%PHP_PATH%" -S localhost:8000
) ELSE (
    echo [INFO] Checking system PATH for php...
    where php >nul 2>nul
    IF %ERRORLEVEL% EQU 0 (
        echo [INFO] Server running at http://localhost:8000
        echo [INFO] Opening browser at http://localhost:8000 ...
        start http://localhost:8000
        php -S localhost:8000
    ) ELSE (
        echo [ERROR] PHP executable not found. Please install XAMPP or add PHP to system PATH.
        pause
    )
)


