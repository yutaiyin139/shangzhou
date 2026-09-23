@echo off

REM ============================================
REM Shangzhou Smart Workbench - Stop Backend ONLY (Flask :5000)
REM ============================================
REM
REM Usage:
REM   stop-backend          Stop backend and pause (double-click friendly)
REM   stop-backend /auto    Stop backend without pausing (for scripting)
REM
REM Note: this stops ONLY the Flask backend on :5000.
REM       Celery worker/beat and Redis/Qdrant are left untouched.
REM       Use stop-all.bat to stop everything.
REM ============================================

title Stop-Backend-5000

echo.
echo ============================================
echo   Stopping Backend (Flask :5000)
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $conns = Get-NetTCPConnection -LocalPort 5000 -State Listen; if ($conns) { $pids = $conns.OwningProcess | Sort-Object -Unique; foreach ($procId in $pids) { Stop-Process -Id $procId -Force }; Write-Host ('[OK] Backend stopped (PID ' + ($pids -join ', ') + ')') } else { Write-Host '[SKIP] Backend not running (port 5000 is free)' }"

echo.
if /i not "%~1"=="/auto" pause
