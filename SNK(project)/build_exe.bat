@echo off
title Build Standalone Executable - Faculty ERP
echo ===============================================================================
echo   AI-ENABLED FACULTY ATTENDANCE, LEAVE AND SUBSTITUTE MANAGEMENT ERP
echo   Executable Packaging Wizard (PyInstaller)
echo ===============================================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run 'setup_environment.bat' first.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

echo [1/3] Checking PyInstaller installation...
python -m pip install pyinstaller --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller
)

echo.
echo [2/3] Compiling standalone desktop executable from faculty_erp.spec...
pyinstaller --clean --noconfirm faculty_erp.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===============================================================================
    echo [SUCCESS] Desktop distribution built successfully!
    echo   Standalone executable folder: .\dist\FacultyERP\
    echo   Application executable:      .\dist\FacultyERP\FacultyERP.exe
    echo ===============================================================================
) else (
    echo.
    echo [ERROR] PyInstaller compilation encountered an issue.
)

echo.
pause
