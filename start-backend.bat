@echo off

REM ============================================
REM Shangzhou Smart Workbench - Start Backend (Flask)

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Usage:
REM   start-backend          Start Flask backend
REM ============================================

title Flask-5000

set "REDIS_DIR=%~dp0Redis-8.10.1"
set "REDIS_CLI=%REDIS_DIR%\redis-cli.exe"

echo.
echo ============================================
echo   Shangzhou Smart Workbench - Backend
echo ============================================
echo.

cd /d "%~dp0backend"

REM Check Python
"%PYTHON%" --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.13
  echo.
  pause
  exit /b 1
)
for /f "tokens=*" %%i in ('"%PYTHON%" --version 2^>^&1') do echo [OK] Python: %%i

REM Check Python dependencies
"%PYTHON%" -c "import flask, flask_cors, pymysql, redis, celery" >nul 2>nul
if errorlevel 1 (
  echo [1/4] Installing Python dependencies...
  "%PYTHON%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
  )
) else (
  echo [1/4] Python dependencies ready
)

REM Check Redis
echo [2/4] Checking Redis service...
if exist "%REDIS_CLI%" (
  "%REDIS_CLI%" ping >nul 2>nul
  if errorlevel 1 (
    echo   [WARN] Redis not running. Please start Redis first.
  ) else (
    echo   [OK] Redis is running
  )
) else (
  echo   [WARN] Redis CLI not found
)

REM Check Qdrant
echo [3/4] Checking Qdrant service...
powershell -Command "try { $r = Invoke-WebRequest -Uri http://localhost:6333/healthz -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo   [WARN] Qdrant not running
) else (
  echo   [OK] Qdrant is running
)

REM Check port 5000
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo [OK] Backend already running (port 5000)
  echo.
  pause
  exit /b 0
)

echo [4/4] Starting backend http://localhost:5000 ...
echo.
echo   Press Ctrl+C to stop
echo.
echo ============================================
echo.

"%PYTHON%" app.py
