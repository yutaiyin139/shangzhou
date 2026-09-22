@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Shangzhou Smart Workbench - One-click Setup

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Steps:
REM   1. Check environment (Python/Node/MySQL/Redis)
REM   2. Install Python dependencies
REM   3. Install frontend dependencies
REM   4. Initialize database
REM   5. Create config files
REM ============================================

title Shangzhou Workbench - Setup

echo.
echo ============================================
echo   Shangzhou Smart Workbench - Setup
echo ============================================
echo.

set "ERRORS=0"

REM Ensure Node.js is in PATH
where node >nul 2>nul
if errorlevel 1 (
  if exist "%ProgramFiles%\nodejs\node.exe" set "PATH=%PATH%;%ProgramFiles%\nodejs"
)

REM ============================================
REM Step 1: Check environment
REM ============================================
echo [1/5] Checking environment...

REM Python
"%PYTHON%" --version >nul 2>nul
if errorlevel 1 (
  echo   [FAIL] Python not found. Please install Python 3.13
  set /a ERRORS+=1
  goto :skip_env
)
for /f "tokens=*" %%i in ('"%PYTHON%" --version 2^>^&1') do echo   [OK] Python: %%i

REM Node.js
where node >nul 2>nul
if errorlevel 1 (
  echo   [FAIL] Node.js not found. Please install Node.js 18+
  set /a ERRORS+=1
  goto :skip_env
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo   [OK] Node.js: %%i

REM PyMySQL
"%PYTHON%" -c "import pymysql; print('OK')" >nul 2>nul
if errorlevel 1 (
  echo   [WARN] PyMySQL not installed, will auto-install
) else (
  echo   [OK] PyMySQL installed
)

REM Redis
"%PYTHON%" -c "import redis; r=redis.Redis(); r.ping(); print('OK')" >nul 2>nul
if errorlevel 1 (
  echo   [WARN] Redis not running or redis-py not installed
) else (
  echo   [OK] Redis connected
)

:skip_env
echo.

REM ============================================
REM Step 2: Install Python dependencies
REM ============================================
echo [2/5] Installing Python dependencies...

cd /d "%~dp0.."

if exist "backend\requirements.txt" (
  "%PYTHON%" -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo   [FAIL] Python dependencies install failed
    set /a ERRORS+=1
  ) else (
    echo   [OK] Python dependencies installed
  )
) else (
  echo   [SKIP] requirements.txt not found
)
echo.

REM ============================================
REM Step 3: Install frontend dependencies
REM ============================================
echo [3/5] Installing frontend dependencies...

if exist "front\package.json" (
  cd front
  if not exist "node_modules" (
    call npm install
    if errorlevel 1 (
      echo   [FAIL] Frontend dependencies install failed
      set /a ERRORS+=1
    ) else (
      echo   [OK] Frontend dependencies installed
    )
  ) else (
    echo   [OK] Frontend dependencies already exist
  )
  cd ..
) else (
  echo   [SKIP] front\package.json not found
)
echo.

REM ============================================
REM Step 4: Initialize database
REM ============================================
echo [4/5] Initializing database...

if exist "backend\models\tables.py" (
  "%PYTHON%" "%~dp0init_db.py" 2>nul
  if errorlevel 1 (
    echo   [WARN] Database init may need manual execution
  )
) else (
  echo   [SKIP] Database table definitions not found
)
echo.

REM ============================================
REM Step 5: Create config files
REM ============================================
echo [5/5] Creating config files...

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo   [OK] Created .env file (please edit configuration)
  ) else (
    echo   [SKIP] .env.example not found
  )
) else (
  echo   [OK] .env file already exists
)

REM Create log directory
if not exist "logs" mkdir logs
echo   [OK] Log directory created

REM Create backup directory
if not exist "backups" mkdir backups
echo   [OK] Backup directory created
echo.

REM ============================================
REM Done
REM ============================================
echo ============================================
if %ERRORS%==0 (
  echo   Setup complete!
  echo.
  echo   Next steps:
  echo   1. Edit .env file with database password
  echo   2. Run start-all.bat to start services
  echo   3. Visit http://localhost:5173
) else (
  echo   Setup finished with %ERRORS% error(s)
  echo   Please check logs above and fix issues
)
echo ============================================
echo.

pause
endlocal
