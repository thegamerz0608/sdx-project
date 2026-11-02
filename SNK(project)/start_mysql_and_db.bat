@echo off
title PostgreSQL Database Initializer (Migrated from MySQL)
echo ===============================================================================
echo [NOTICE] This ERP system has migrated from MySQL/MariaDB to PostgreSQL 16!
echo Forwarding execution to 'start_postgres_and_db.bat'...
echo ===============================================================================
echo.
cd /d "%~dp0"
call start_postgres_and_db.bat
