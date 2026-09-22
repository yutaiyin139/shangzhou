@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Shangzhou Smart Workbench - MySQL Backup Tool

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Usage:
REM   backup-mysql            Backup szagent database
REM   backup-mysql --full     Backup all databases
REM   backup-mysql --restore  Restore from latest backup
REM   backup-mysql --list     List all backups
REM
REM Requires: PyMySQL (pip install pymysql)
REM ============================================

title MySQL Backup Tool

echo.
echo ============================================
echo   Shangzhou Smart Workbench - MySQL Backup
echo ============================================
echo.

REM Parse arguments
set "MODE=backup"
set "EXTRA_ARGS="

:parse_args
if "%~1"=="" goto :done_parse
if /i "%~1"=="--full" (
  set "MODE=backup"
  set "EXTRA_ARGS=--full"
)
if /i "%~1"=="--restore" set "MODE=restore"
if /i "%~1"=="--list" set "MODE=list"
shift
goto :parse_args
:done_parse

REM Check PyMySQL
"%PYTHON%" -c "import pymysql" >nul 2>nul
if errorlevel 1 (
  echo [WARN] PyMySQL not installed. Installing...
  "%PYTHON%" -m pip install pymysql
  if errorlevel 1 (
    echo [ERROR] Failed to install PyMySQL
    pause
    exit /b 1
  )
)

REM Create backup directory
if not exist "%~dp0..\backups" mkdir "%~dp0..\backups"

REM Run backup tool
"%PYTHON%" "%~dp0db_backup.py" %MODE% %EXTRA_ARGS%

echo.
pause
endlocal
