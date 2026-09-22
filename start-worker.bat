@echo off

REM ============================================
REM Shangzhou Smart Workbench - Start Celery Worker

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Usage:
REM   start-worker          Start Worker + Beat
REM ============================================

title Celery-Worker

set "REDIS_CLI=%~dp0Redis-8.10.1\redis-cli.exe"

echo.
echo ============================================
echo   Shangzhou Smart Workbench - Celery Worker
echo ============================================
echo.

cd /d "%~dp0backend"

REM Check Redis is running
"%REDIS_CLI%" ping >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Redis not running! Please start Redis or run start-all.bat
  echo.
  pause
  exit /b 1
)

echo [OK] Redis connected
echo.
echo   Features: async task processing + scheduled tasks (Beat)
echo   Queues:   workflow, embedding, scheduled
echo.
echo   Press Ctrl+C to stop both Worker and Beat
echo.
echo ============================================
echo.

REM Start Worker and Beat as separate processes (Windows incompatible with -B flag)
start "Celery-Worker" cmd /k "cd /d %~dp0backend && "%PYTHON%" -m celery -A tasks.celery_app worker --loglevel=info -Q workflow,embedding,scheduled"
start "Celery-Beat" cmd /k "cd /d %~dp0backend && "%PYTHON%" -m celery -A tasks.celery_app beat --loglevel=info"
echo.
echo   Worker and Beat started in separate windows.
