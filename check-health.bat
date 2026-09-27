@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Shangzhou Smart Workbench - Health Check

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Usage:
REM   check-health         Check all services
REM   check-health --json  Output JSON (for programmatic use)
REM   check-health --watch Watch mode (refresh every 30s)
REM ============================================

title Shangzhou Workbench - Health Check

set "REDIS_CLI=%~dp0Redis-8.10.1\redis-cli.exe"
set "JSON_MODE=0"
set "WATCH_MODE=0"
set "OK_COUNT=0"
set "FAIL_COUNT=0"
set "WARN_COUNT=0"

REM Read DB/Redis host:port from project-root .env (dev DB may be remote; never assume localhost)
REM WARNING: `for /f ... in (file)` silently DROPS a KEY=VALUE line that follows a UTF-8 Chinese
REM comment line, because cmd's codepage-936 reader pairs the comment's trailing byte with the
REM newline. Measured on this .env: 7 of 73 keys lost, including DB_HOST/DB_USER/REDIS_HOST.
REM findstr splits lines byte-wise and is immune, so always pre-filter the file through findstr.
set "DB_HOST=localhost"
set "DB_PORT=3306"
set "REDIS_HOST=localhost"
set "REDIS_PORT=6379"
if exist "%~dp0.env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /r "DB_HOST= DB_PORT= REDIS_HOST= REDIS_PORT=" "%~dp0.env"`) do (
    if /i "%%~A"=="DB_HOST"    set "DB_HOST=%%~B"
    if /i "%%~A"=="DB_PORT"    set "DB_PORT=%%~B"
    if /i "%%~A"=="REDIS_HOST" set "REDIS_HOST=%%~B"
    if /i "%%~A"=="REDIS_PORT" set "REDIS_PORT=%%~B"
  )
)

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_parse
if /i "%~1"=="--json" set "JSON_MODE=1"
if /i "%~1"=="--watch" set "WATCH_MODE=1"
shift
goto :parse_args
:done_parse

REM JSON mode: no decoration
if %JSON_MODE%==0 (
  echo.
  echo ============================================
  echo   Shangzhou Smart Workbench - Health Check
  echo   Time: %date% %time%
  echo ============================================
  echo.
) else (
  echo {"timestamp":"%date% %time%","services":[
)

REM ============================================
REM Check Redis
REM ============================================
set "REDIS_STATUS=FAIL"
set "REDIS_DETAIL=not running"

"%REDIS_CLI%" -h %REDIS_HOST% -p %REDIS_PORT% ping >nul 2>nul
if not errorlevel 1 (
  for /f "tokens=*" %%i in ('"%REDIS_CLI%" -h %REDIS_HOST% -p %REDIS_PORT% ping 2^>nul') do (
    if "%%i"=="PONG" (
      set "REDIS_STATUS=OK"
      set "REDIS_DETAIL=running"
      set /a OK_COUNT+=1
    )
  )
) else (
  set /a FAIL_COUNT+=1
)

REM Get Redis version info. Do NOT pipe through findstr here: a quoted exe path combined with
REM `|` inside `for /f ('...')` makes cmd build an invalid command line and the loop yields
REM nothing plus "The syntax for the file name, a directory name, or a volume label is incorrect".
REM Also keep parentheses out of the value: it is echoed inside `if ( ... )` blocks later.
if "%REDIS_STATUS%"=="OK" (
  for /f "tokens=1,* delims=:" %%a in ('"%REDIS_CLI%" -h %REDIS_HOST% -p %REDIS_PORT% INFO server') do (
    if /i "%%a"=="redis_version" set "REDIS_DETAIL=running v%%b"
  )
)

if %JSON_MODE%==1 (
  echo   {"name":"redis","port":%REDIS_PORT%,"status":"%REDIS_STATUS%","detail":"%REDIS_DETAIL%"},
) else (
  if "%REDIS_STATUS%"=="OK" (
    echo   [OK]   Redis    - %REDIS_HOST%:%REDIS_PORT%  - %REDIS_DETAIL%
  ) else (
    echo   [FAIL] Redis    - %REDIS_HOST%:%REDIS_PORT%  - %REDIS_DETAIL%
  )
)

REM ============================================
REM Check Qdrant
REM ============================================
set "QDRANT_STATUS=FAIL"
set "QDRANT_DETAIL=not running"

powershell -Command "try { $r = Invoke-WebRequest -Uri http://localhost:6333/healthz -UseBasicParsing -TimeoutSec 10; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
  set "QDRANT_STATUS=OK"
  set "QDRANT_DETAIL=running"
  set /a OK_COUNT+=1
) else (
  set /a FAIL_COUNT+=1
)

if %JSON_MODE%==1 (
  echo   {"name":"qdrant","port":6333,"status":"%QDRANT_STATUS%","detail":"%QDRANT_DETAIL%"},
) else (
  if "%QDRANT_STATUS%"=="OK" (
    echo   [OK]   Qdrant   - localhost:6333  - %QDRANT_DETAIL%
  ) else (
    echo   [FAIL] Qdrant   - localhost:6333  - %QDRANT_DETAIL%
  )
)

REM ============================================
REM Check MySQL (TCP probe DB_HOST:DB_PORT taken from .env; works for remote DB)
REM ============================================
set "MYSQL_STATUS=FAIL"
set "MYSQL_DETAIL=not reachable"

powershell -NoProfile -Command "$c=New-Object System.Net.Sockets.TcpClient; try { $r=$c.BeginConnect('!DB_HOST!',!DB_PORT!,$null,$null); if ($r.AsyncWaitHandle.WaitOne(3000) -and $c.Connected) { exit 0 } else { exit 1 } } catch { exit 1 } finally { $c.Close() }"
if not errorlevel 1 (
  set "MYSQL_STATUS=OK"
  set "MYSQL_DETAIL=reachable"
  set /a OK_COUNT+=1
) else (
  set "MYSQL_DETAIL=!DB_HOST!:!DB_PORT! unreachable"
  set /a FAIL_COUNT+=1
)

if %JSON_MODE%==1 (
  echo   {"name":"mysql","host":"!DB_HOST!","port":!DB_PORT!,"status":"!MYSQL_STATUS!","detail":"!MYSQL_DETAIL!"},
) else (
  if "!MYSQL_STATUS!"=="OK" (
    echo   [OK]   MySQL    - !DB_HOST!:!DB_PORT!  - !MYSQL_DETAIL!
  ) else (
    echo   [FAIL] MySQL    - !DB_HOST!:!DB_PORT!  - !MYSQL_DETAIL!
  )
)

REM ============================================
REM Check Flask Backend
REM ============================================
set "BACKEND_STATUS=FAIL"
set "BACKEND_DETAIL=not running"

powershell -Command "try { $r = Invoke-WebRequest -Uri http://localhost:5000/api/health -UseBasicParsing -TimeoutSec 10; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
  set "BACKEND_STATUS=OK"
  set "BACKEND_DETAIL=running"
  set /a OK_COUNT+=1
) else (
  set /a FAIL_COUNT+=1
)

REM Check if port is occupied (may be starting)
if "%BACKEND_STATUS%"=="FAIL" (
  netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>nul
  if not errorlevel 1 (
    set "BACKEND_STATUS=WARN"
    set "BACKEND_DETAIL=port occupied but health check failed"
    set /a WARN_COUNT+=1
  )
)

if %JSON_MODE%==1 (
  echo   {"name":"backend","port":5000,"status":"%BACKEND_STATUS%","detail":"%BACKEND_DETAIL%"},
) else (
  if "%BACKEND_STATUS%"=="OK" (
    echo   [OK]   Flask    - localhost:5000  - %BACKEND_DETAIL%
  ) else if "%BACKEND_STATUS%"=="WARN" (
    echo   [WARN] Flask    - localhost:5000  - %BACKEND_DETAIL%
  ) else (
    echo   [FAIL] Flask    - localhost:5000  - %BACKEND_DETAIL%
  )
)

REM ============================================
REM Check Vite Frontend
REM ============================================
set "FRONTEND_STATUS=FAIL"
set "FRONTEND_DETAIL=not running"

powershell -Command "try { $r = Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing -TimeoutSec 10; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
  set "FRONTEND_STATUS=OK"
  set "FRONTEND_DETAIL=running"
  set /a OK_COUNT+=1
) else (
  set /a FAIL_COUNT+=1
)

if %JSON_MODE%==1 (
  echo   {"name":"frontend","port":5173,"status":"%FRONTEND_STATUS%","detail":"%FRONTEND_DETAIL%"},
) else (
  if "%FRONTEND_STATUS%"=="OK" (
    echo   [OK]   Vite     - localhost:5173  - %FRONTEND_DETAIL%
  ) else (
    echo   [FAIL] Vite     - localhost:5173  - %FRONTEND_DETAIL%
  )
)

REM ============================================
REM Check Celery Worker
REM ============================================
set "WORKER_STATUS=FAIL"
set "WORKER_DETAIL=not running"

powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'celery' }) { exit 0 } else { exit 1 }" >nul 2>nul
if not errorlevel 1 (
  set "WORKER_STATUS=OK"
  set "WORKER_DETAIL=running"
  set /a OK_COUNT+=1
) else (
  set /a FAIL_COUNT+=1
)

if %JSON_MODE%==1 (
  echo   {"name":"worker","port":"-","status":"%WORKER_STATUS%","detail":"%WORKER_DETAIL%"}
  echo  ],"summary":{"ok":%OK_COUNT%,"fail":%FAIL_COUNT%,"warn":%WARN_COUNT%}}
) else (
  if "%WORKER_STATUS%"=="OK" (
    echo   [OK]   Worker   - Celery async   - %WORKER_DETAIL%
  ) else (
    echo   [FAIL] Worker   - Celery async   - %WORKER_DETAIL%
  )
)

REM ============================================
REM Summary
REM ============================================
if %JSON_MODE%==0 (
  echo.
  echo ============================================
  echo   Summary: %OK_COUNT% OK / %FAIL_COUNT% FAIL / %WARN_COUNT% WARN
  echo ============================================
  echo.

  if %FAIL_COUNT% gtr 0 (
    echo [TIP] Some services are down:
    echo       1. Run start-all.bat to start missing services
    echo       2. Check service window logs for errors
    echo.
  )

  if %OK_COUNT% geq 5 (
    echo [STATUS] All core services are running.
    echo.
  )
)

REM Watch mode
if %WATCH_MODE%==1 (
  echo.
  echo --watch mode: refreshing in 30 seconds ^(Ctrl+C to exit^)...
  ping -n 31 127.0.0.1 >nul
  cls
  goto :done_parse
)

if %JSON_MODE%==0 pause
endlocal
