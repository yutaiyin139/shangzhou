@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Shangzhou Smart Workbench - v1.0 Release Cleanup
REM
REM Cleans: temp files / caches / old code
REM Keeps:  dify-1.17.0 folder (reference)
REM
REM Cleanup list:
REM   1. Python cache (__pycache__, *.pyc)
REM   2. Backend cache (backend/cache/)
REM   3. Frontend build output (front/dist/)
REM   4. Frontend legacy HTML (front/legacy/)
REM   5. Frontend deps (front/node_modules/) - recoverable via npm install
REM   6. Backend one-off scripts (migration/diagnostic tools)
REM   7. Backend vendored libs (venv_libs/)
REM   8. Qdrant runtime data
REM   9. Temp/useless files
REM ============================================

title Shangzhou Workbench - v1.0 Release Cleanup

echo.
echo ============================================
echo   Shangzhou Smart Workbench - v1.0 Cleanup
echo ============================================
echo.
echo   WARNING: This will delete temp files and caches
echo   NOTE:    dify-1.17.0 folder will NOT be deleted
echo.
echo ============================================
echo.

set /p CONFIRM=Continue? (type YES to proceed):
if /i not "%CONFIRM%"=="YES" (
  echo Cleanup cancelled.
  goto :eof
)

set "DELETED_COUNT=0"

REM ============================================
REM Step 1: Clean Python cache
REM ============================================
echo [1/9] Cleaning Python cache files...

for /r "%~dp0.." %%d in (__pycache__) do (
  if exist "%%d" (
    rd /s /q "%%d" 2>nul
    set /a DELETED_COUNT+=1
  )
)

del /s /q "%~dp0..\*.pyc" >nul 2>nul
del /s /q "%~dp0..\*.pyo" >nul 2>nul
echo   Done

REM ============================================
REM Step 2: Clean backend cache
REM ============================================
echo [2/9] Cleaning backend cache (backend/cache/)...

if exist "%~dp0..\backend\cache\templates" (
  rd /s /q "%~dp0..\backend\cache\templates" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 3: Clean frontend build output
REM ============================================
echo [3/9] Cleaning frontend build output (front/dist/)...

if exist "%~dp0..\front\dist" (
  rd /s /q "%~dp0..\front\dist" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 4: Clean frontend legacy HTML
REM ============================================
echo [4/9] Cleaning frontend legacy HTML (front/legacy/)...

if exist "%~dp0..\front\legacy" (
  rd /s /q "%~dp0..\front\legacy" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 5: Clean frontend deps (recoverable via npm install)
REM ============================================
echo [5/9] Cleaning frontend deps (front/node_modules/)...

if exist "%~dp0..\front\node_modules" (
  rd /s /q "%~dp0..\front\node_modules" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done (run npm install to restore)

REM ============================================
REM Step 6: Clean backend one-off scripts
REM ============================================
echo [6/9] Cleaning backend one-off scripts...

if exist "%~dp0..\backend\cleanup_users.py" (
  del /q "%~dp0..\backend\cleanup_users.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\cleanup_users.sql" (
  del /q "%~dp0..\backend\cleanup_users.sql" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\diagnose.py" (
  del /q "%~dp0..\backend\diagnose.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\migrate_from_dify.py" (
  del /q "%~dp0..\backend\migrate_from_dify.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\migrate_merge_tables.py" (
  del /q "%~dp0..\backend\migrate_merge_tables.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\migrate_users.py" (
  del /q "%~dp0..\backend\migrate_users.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\reset_password.py" (
  del /q "%~dp0..\backend\reset_password.py" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\backend\=5.0.0" (
  del /q "%~dp0..\backend\=5.0.0" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 7: Clean backend vendored libs
REM ============================================
echo [7/9] Cleaning backend vendored libs (venv_libs/)...

if exist "%~dp0..\backend\venv_libs" (
  rd /s /q "%~dp0..\backend\venv_libs" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 8: Clean Qdrant runtime data
REM ============================================
echo [8/9] Cleaning Qdrant runtime data...

if exist "%~dp0..\qdrant\storage" (
  rd /s /q "%~dp0..\qdrant\storage" 2>nul
  md "%~dp0..\qdrant\storage" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\qdrant\snapshots" (
  rd /s /q "%~dp0..\qdrant\snapshots" 2>nul
  md "%~dp0..\qdrant\snapshots" 2>nul
  set /a DELETED_COUNT+=1
)
if exist "%~dp0..\qdrant\.qdrant-initialized" (
  del /q "%~dp0..\qdrant\.qdrant-initialized" 2>nul
  set /a DELETED_COUNT+=1
)
echo   Done

REM ============================================
REM Step 9: Clean other temp files
REM ============================================
echo [9/9] Cleaning other temp files...

REM Frontend conversion script
if exist "%~dp0..\front\convert_html_to_vue.py" (
  del /q "%~dp0..\front\convert_html_to_vue.py" 2>nul
  set /a DELETED_COUNT+=1
)

REM Keep scripts/backup-mysql.bat (used for backups)
if exist "%~dp0backup-mysql.bat" (
  echo   Keeping scripts\backup-mysql.bat
)
echo   Done

REM ============================================
REM Summary
REM ============================================
echo.
echo ============================================
echo   Cleanup complete!
echo ============================================
echo.
echo   Items deleted: %DELETED_COUNT%
echo.
echo   Core files kept:
echo     - backend/app.py (main entry)
echo     - backend/config.py (config)
echo     - backend/routes/ (routes)
echo     - backend/models/ (models)
echo     - backend/engine/ (engine)
echo     - backend/tasks/ (async tasks)
echo     - backend/utils/ (utils)
echo     - front/src/ (frontend source)
echo     - front/package.json (deps config)
echo     - Redis-8.10.1/ (Redis service)
echo     - qdrant/ (vector DB)
echo     - dify-1.17.0/ (reference)
echo     - docs/ (documentation)
echo     - scripts/ (scripts)
echo     - *.bat (start/stop scripts)
echo.
echo   Next steps:
echo     1. Run npm install to restore frontend deps
echo     2. Run pip install -r requirements.txt to restore backend deps
echo     3. Run start-all.bat to start services
echo.
echo ============================================
echo.

endlocal
pause
