@echo off
title Smartphone Biometric Bridge Daemon
echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE ERP - BIOMETRIC BRIDGE DAEMON
echo   FastAPI + WebAuthn Biometrics + Automated Tunnel Fallback
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python Virtual Environment
if not exist "venv\Scripts\activate.bat" goto no_venv
goto venv_ok

:no_venv
echo [ERROR] Virtual environment not found at venv\Scripts\activate.bat
echo Please run setup_environment.bat first to configure the environment.
pause
exit /b 1

:venv_ok
:: 2. Check Node.js / npx Availability (Required for LocalTunnel fallback)
where npx >nul 2>&1
if %ERRORLEVEL% EQU 0 goto npx_found

echo [WARNING] Node.js and npx were not detected in system PATH.
echo           If Windows Application Control blocks ngrok.exe,
echo           LocalTunnel fallback will not be available.
echo           To enable LocalTunnel, install Node.js from https://nodejs.org/
echo.
goto activate_venv

:npx_found
echo [OK] Node.js and npx detected - LocalTunnel HTTPS fallback ready.
echo.

:activate_venv
:: 3. Activate Python Environment
echo [INFO] Activating virtual environment...
call "venv\Scripts\activate.bat"

echo.
echo ===============================================================================
echo   AUTOMATED CLEANUP REMINDER:
echo   When you shut down this window or press Ctrl+C:
echo   - Any active ngrok or localtunnel background processes will be terminated.
echo   - The temporary public URL in the SYSTEM_SETTINGS table will be wiped.
echo   - BIOMETRIC_DAEMON_STATUS will automatically reset to INACTIVE.
echo ===============================================================================
echo.

:: 4. Start Python Daemon
python biometric_daemon.py %*

if %ERRORLEVEL% EQU 0 goto daemon_done
echo.
echo [NOTE] Biometric Daemon process exited with code %ERRORLEVEL%.
pause

:daemon_done
