@echo off

REM ============================================
REM Shangzhou Smart Workbench - Stop Frontend ONLY (Vite :5173)
REM ============================================
REM
REM Usage:
REM   stop-front            Stop frontend and pause (double-click friendly)
REM   stop-front /auto      Stop frontend without pausing (for scripting)
REM
REM Note: this stops ONLY the Vite dev server on :5173.
REM       Backend / Celery / Redis / Qdrant are left untouched.
REM       Use stop-all.bat to stop everything.
REM ============================================

title Stop-Frontend-5173

echo.
echo ============================================
echo   Stopping Frontend (Vite :5173)
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $conns = Get-NetTCPConnection -LocalPort 5173 -State Listen; if ($conns) { $pids = $conns.OwningProcess | Sort-Object -Unique; foreach ($procId in $pids) { Stop-Process -Id $procId -Force }; Write-Host ('[OK] Frontend stopped (PID ' + ($pids -join ', ') + ')') } else { Write-Host '[SKIP] Frontend not running (port 5173 is free)' }"

echo.
if /i not "%~1"=="/auto" pause
