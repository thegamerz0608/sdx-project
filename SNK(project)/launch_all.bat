@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title AI-Enabled Faculty Attendance ERP - Master Launcher

echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE, LEAVE AND SUBSTITUTE MANAGEMENT ERP
echo   Master Simultaneous Launcher [Biometric Daemon + Kiosk + Desktop + erp.sys]
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Verify Virtual Environment
if not exist "venv\Scripts\activate.bat" goto :no_venv
goto :check_postgres

:no_venv
echo [ERROR] Virtual environment not found at venv\Scripts\activate.bat
echo Please run setup_environment.bat first to configure dependencies.
pause
exit /b 1

:check_postgres
:: 2. Check PostgreSQL Service Status on Port 5432
netstat -ano | findstr /R ":5432.*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL service active on port 5432.
) else (
    echo [INFO] PostgreSQL on port 5432 not detected. If running in Docker: docker compose up -d
)

:: 3. Check and Register 'erp.sys' Local Domain Alias
set "HOSTS_FILE=%SystemRoot%\System32\drivers\etc\hosts"
findstr /I /C:"erp.sys" "%HOSTS_FILE%" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :domain_ok

echo [INFO] Domain alias 'erp.sys' not yet registered in Windows hosts.
echo        Attempting automated background registration for 127.0.0.1 erp.sys...
powershell -Command "Start-Process powershell -ArgumentList '-Command \"Add-Content -Path ''$env:SystemRoot\System32\drivers\etc\hosts'' -Value ''`n127.0.0.1       erp.sys'' ; ipconfig /flushdns\"' -Verb RunAs" >nul 2>&1
goto :launch_services

:domain_ok
echo [OK] Local domain alias 'erp.sys' is mapped and active.

:launch_services
echo.
echo -------------------------------------------------------------------------------
echo [1/2] Launching Standalone Biometric Bridge Daemon on Port 8000...
echo -------------------------------------------------------------------------------
start "Biometric Server Daemon [erp.sys:8000]" cmd /k "title Biometric Server Daemon [erp.sys:8000] & cd /d ""%~dp0"" & call venv\Scripts\activate.bat & python biometric_daemon.py"

:: Wait 3 seconds for FastAPI and ngrok/LocalTunnel to initialize
echo [INFO] Synchronizing background server and database settings...
timeout /t 3 /nobreak >nul 2>&1 || ping -n 4 127.0.0.1 >nul 2>&1

echo.
echo -------------------------------------------------------------------------------
echo [2/2] Launching Desktop ERP Application and Biometric Terminal Kiosk...
echo -------------------------------------------------------------------------------
start "Faculty ERP Desktop App" cmd /c "title Faculty ERP Desktop Application & cd /d ""%~dp0"" & call venv\Scripts\activate.bat & python main.py"

echo.
echo ===============================================================================
echo   ALL SYSTEMS INITIALIZED AND RUNNING SIMULTANEOUSLY:
echo.
echo   * Desktop Application     : Active [Institutional Login Screen]
echo   * Biometric Terminal      : Active [Full Kiosk Mode with Title Bar Controls]
echo   * Biometric FastAPI Daemon : Running on Port 8000 [Console Open]
echo.
echo   * Clean Institutional Web Portal Links:
echo       - Admin Security Gateway : http://erp.sys:8000/admin-login
echo       - Faculty/Staff Portal   : http://erp.sys:8000/staff-login
echo       - Mobile Biometric Punch : http://erp.sys:8000/punch-interface
echo       - Localhost Fallback     : http://127.0.0.1:8000/admin-login
echo       - Local Wi-Fi Network    : http://192.168.70.123:8000/admin-login
echo.
echo   * Global Internet Access [For other computers on DIFFERENT internet]:
echo       - Run: launch_public_internet_access.bat
echo       - Generates encrypted public HTTPS links accessible from anywhere worldwide!
echo ===============================================================================
echo.
echo You can keep this launcher console open or close it at any time.
echo To shut down all services, close the Biometric Daemon and ERP windows.
echo.
pause
