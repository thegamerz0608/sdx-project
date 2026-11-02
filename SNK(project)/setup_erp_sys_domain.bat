@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title Configure erp.sys Local Domain Alias
echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE ERP - LOCAL DOMAIN SETUP [erp.sys]
echo ===============================================================================
echo.

:: Check for Administrator Elevation
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :is_admin

echo [ELEVATION REQUIRED] Requesting Administrator privileges...
powershell -Command "Start-Process '%~f0' -Verb RunAs"
exit /b

:is_admin
set "HOSTS_FILE=%SystemRoot%\System32\drivers\etc\hosts"

echo [*] Checking Windows hosts configuration at %HOSTS_FILE%...
findstr /I /C:"erp.sys" "%HOSTS_FILE%" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :already_mapped

echo [*] Appending '127.0.0.1 erp.sys' to Windows hosts file...
echo. >> "%HOSTS_FILE%"
echo # Faculty Attendance ERP Local Domain Alias >> "%HOSTS_FILE%"
echo 127.0.0.1       erp.sys >> "%HOSTS_FILE%"
if %ERRORLEVEL% NEQ 0 goto :hosts_error

echo [SUCCESS] Domain alias 'erp.sys' added successfully!
goto :flush_dns

:hosts_error
echo [ERROR] Failed to update hosts file. Please ensure you have Administrator permissions.
pause
exit /b 1

:already_mapped
echo [OK] 'erp.sys' domain alias is already mapped in your hosts file.

:flush_dns
echo [*] Flushing Windows DNS resolver cache...
ipconfig /flushdns >nul 2>&1

echo.
echo ===============================================================================
echo   CONFIGURATION COMPLETE! You can now use clean institutional links:
echo.
echo   * Administrator Security Gateway : http://erp.sys:8000/admin-login
echo   * Faculty & Staff CMS Portal    : http://erp.sys:8000/staff-login
echo   * Mobile Biometric Punch Gate   : http://erp.sys:8000/punch-interface
echo ===============================================================================
echo.
pause
