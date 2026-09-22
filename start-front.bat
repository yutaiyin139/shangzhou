@echo off

REM ============================================
REM Shangzhou Smart Workbench - Start Frontend (Vue3 + Vite)
REM
REM Usage:
REM   start-front          Start frontend dev server
REM ============================================

title Vite-5173

REM Ensure Node.js is in PATH
where node >nul 2>nul
if errorlevel 1 (
  if exist "%ProgramFiles%\nodejs\node.exe" set "PATH=%PATH%;%ProgramFiles%\nodejs"
)

echo.
echo ============================================
echo   Shangzhou Smart Workbench - Frontend
echo ============================================
echo.

cd /d "%~dp0front"

REM Check Node.js
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js not found. Please install Node.js 18+
  echo.
  pause
  exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node.js: %%i

REM Check if port 5173 is in use
netstat -ano | findstr ":5173 " | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo [OK] Frontend already running (port 5173)
  echo.
  pause
  exit /b 0
)

REM Check and install dependencies
if not exist node_modules (
  echo [1/2] First run, installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
  )
) else (
  echo [1/2] Frontend dependencies ready
)

echo [2/2] Starting dev server http://localhost:5173 ...
echo.
echo   Press Ctrl+C to stop
echo.
echo ============================================
echo.

call npm run dev
