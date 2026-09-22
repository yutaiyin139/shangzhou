@echo off

REM ============================================
REM Shangzhou Smart Workbench - Start All Services
REM ============================================
REM
REM This wrapper delegates to start-services.ps1 which
REM works reliably from both CMD and Git Bash.
REM ============================================

REM Ensure logs directory exists
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM Run PowerShell script with bypass execution policy
powershell -ExecutionPolicy Bypass -File "%~dp0start-services.ps1"

REM Pause if there were errors
if errorlevel 1 (
  echo.
  echo Press any key to exit...
  pause >nul
)
