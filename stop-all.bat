@echo off

REM ============================================
REM Shangzhou Smart Workbench - Stop All Services
REM ============================================
REM
REM This wrapper delegates to stop-services.ps1 which
REM works reliably from both CMD and Git Bash.
REM
REM Options:
REM   --keep-redis    Keep Redis running
REM   --keep-qdrant   Keep Qdrant running
REM   --force         Force kill
REM ============================================

REM Parse arguments and convert to PowerShell parameters
set "PS_ARGS="

:parse_args
if "%~1"=="" goto :done_parse
if /i "%~1"=="--keep-redis" set "PS_ARGS=%PS_ARGS% -KeepRedis"
if /i "%~1"=="--keep-qdrant" set "PS_ARGS=%PS_ARGS% -KeepQdrant"
if /i "%~1"=="--force" set "PS_ARGS=%PS_ARGS% -Force"
shift
goto :done_parse
:done_parse

powershell -ExecutionPolicy Bypass -File "%~dp0stop-services.ps1"%PS_ARGS%
