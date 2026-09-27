@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Shangzhou Smart Workbench - MySQL Backup Tool

REM Use Python 3.13 (3.14 incompatible with Celery on Windows)
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
REM
REM Usage:
REM   backup-mysql            Backup szagent database
REM   backup-mysql --full     Backup all databases
REM   backup-mysql --restore  Restore from latest backup
REM   backup-mysql --list     List all backups
REM ============================================

title MySQL Backup Tool

echo.
echo ============================================
echo   Shangzhou Smart Workbench - MySQL Backup
echo ============================================
echo.

REM Config
set "BACKUP_DIR=%~dp0backups"
set "MYSQL_PATH="
REM DB config comes from project-root .env (dev DB is remote now; do not hardcode localhost/root)
REM WARNING: `for /f ... in (file)` silently DROPS a KEY=VALUE line that follows a UTF-8 Chinese
REM comment line (cmd's codepage-936 reader pairs the trailing byte with the newline). That would
REM leave MYSQL_HOST=localhost / MYSQL_USER=root and back up the wrong server. findstr splits
REM lines byte-wise and is immune, so the file is always pre-filtered through findstr.
set "MYSQL_HOST=localhost"
set "MYSQL_PORT=3306"
set "MYSQL_USER=root"
set "MYSQL_PASS="
set "DB_NAME=szagent"
set "MODE=single"

if exist "%~dp0.env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /r "DB_HOST= DB_PORT= DB_USER= DB_PASSWORD= DB_NAME=" "%~dp0.env"`) do (
    if /i "%%~A"=="DB_HOST"     set "MYSQL_HOST=%%~B"
    if /i "%%~A"=="DB_PORT"     set "MYSQL_PORT=%%~B"
    if /i "%%~A"=="DB_USER"     set "MYSQL_USER=%%~B"
    if /i "%%~A"=="DB_PASSWORD" set "MYSQL_PASS=%%~B"
    if /i "%%~A"=="DB_NAME"     set "DB_NAME=%%~B"
  )
)

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_parse
if /i "%~1"=="--full" set "MODE=full"
if /i "%~1"=="--restore" set "MODE=restore"
if /i "%~1"=="--list" set "MODE=list"
shift
goto :parse_args
:done_parse

REM Find MySQL
where mysqldump >nul 2>nul
if not errorlevel 1 (
  for /f "tokens=*" %%i in ('where mysqldump') do set "MYSQL_PATH=%%i"
  goto :found_mysql
)

REM Common MySQL install paths
for %%p in (
  "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
  "C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
  "C:\xampp\mysql\bin\mysqldump.exe"
  "C:\wamp64\bin\mysql\mysql8.0.31\bin\mysqldump.exe"
) do (
  if exist "%%~p" (
    set "MYSQL_PATH=%%~p"
    goto :found_mysql
  )
)

echo [ERROR] mysqldump.exe not found
echo         Please ensure MySQL is installed and added to PATH
echo.
pause
exit /b 1

:found_mysql
echo [OK] MySQL: %MYSQL_PATH%

REM Default password if empty
if "%MYSQL_PASS%"=="" (
  set "MYSQL_PASS=0000"
  echo [WARN] Using default password. Set DB_PASSWORD env variable for security.
)

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Generate timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,4%%dt:~4,2%%dt:~6,2%_%dt:~8,2%%dt:~10,2%%dt:~12,2%"

REM ============================================
REM List backups
REM ============================================
if "%MODE%"=="list" (
  echo.
  echo [Backup List]
  echo ----------------------------------------------
  if exist "%BACKUP_DIR%\*.sql" (
    dir /b /o-d "%BACKUP_DIR%\*.sql"
  ) else (
    echo   No backup files found
  )
  echo.
  echo Backup directory: %BACKUP_DIR%
  echo.
  pause
  exit /b 0
)

REM ============================================
REM Restore mode
REM ============================================
if "%MODE%"=="restore" (
  echo.
  echo [Restore Mode]
  echo ----------------------------------------------

  REM Find latest backup
  set "LATEST_BACKUP="
  for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\*.sql" 2^>nul') do (
    if not defined LATEST_BACKUP set "LATEST_BACKUP=%%f"
  )

  if not defined LATEST_BACKUP (
    echo [ERROR] No backup files found
    echo.
    pause
    exit /b 1
  )

  echo Latest backup: !LATEST_BACKUP!
  echo.
  set /p CONFIRM="Confirm restore? This will overwrite existing data (y/N): "
  if /i not "!CONFIRM!"=="y" (
    echo Cancelled
    pause
    exit /b 0
  )

  echo.
  echo [1/2] Restoring database...

  for %%p in (
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
    "C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysql.exe"
    "C:\xampp\mysql\bin\mysql.exe"
  ) do (
    if exist "%%~p" (
      "%%~p" -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASS% %DB_NAME% < "%BACKUP_DIR%\!LATEST_BACKUP!"
      if not errorlevel 1 (
        echo [OK] Restore complete
      ) else (
        echo [ERROR] Restore failed
      )
      echo.
      pause
      exit /b 0
    )
  )
  echo [ERROR] mysql.exe not found
  echo.
  pause
  exit /b 1
)

REM ============================================
REM Backup mode
REM ============================================
echo.
if "%MODE%"=="full" (
  echo [Mode] Full database backup
  set "BACKUP_FILE=full_%TIMESTAMP%.sql"
) else (
  echo [Mode] Single database backup (%DB_NAME%)
  set "BACKUP_FILE=%DB_NAME%_%TIMESTAMP%.sql"
)

echo [Target] %BACKUP_DIR%\%BACKUP_FILE%
echo.

REM Execute backup
echo [1/2] Backing up...

if "%MODE%"=="full" (
  "%MYSQL_PATH%" -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASS% ^
    --single-transaction --routines --triggers --events ^
    --all-databases ^
    > "%BACKUP_DIR%\%BACKUP_FILE%" 2>nul
) else (
  "%MYSQL_PATH%" -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASS% ^
    --single-transaction --routines --triggers --events ^
    %DB_NAME% ^
    > "%BACKUP_DIR%\%BACKUP_FILE%" 2>nul
)

if errorlevel 1 (
  echo [ERROR] Backup failed! Please check:
  echo         1. MySQL service is running
  echo         2. Username/password are correct
  echo         3. Write permission on backup directory
  echo.
  pause
  exit /b 1
)

REM Compress backup (if 7z available)
where 7z >nul 2>nul
if not errorlevel 1 (
  echo [2/2] Compressing backup...
  7z a -tzip "%BACKUP_DIR%\%BACKUP_FILE%.zip" "%BACKUP_DIR%\%BACKUP_FILE%" >nul 2>nul
  if not errorlevel 1 (
    del "%BACKUP_DIR%\%BACKUP_FILE%"
    set "BACKUP_FILE=%BACKUP_FILE%.zip"
  )
) else (
  echo [2/2] Skipping compression (7-Zip not installed)
)

REM Clean old backups (keep last 7 days)
echo [Clean] Removing backups older than 7 days...
forfiles /p "%BACKUP_DIR%" /s /m *.sql* /d -7 /c "cmd /c del @path" 2>nul

REM Done
echo.
echo ============================================
echo   Backup complete!
echo   File: %BACKUP_DIR%\%BACKUP_FILE%
echo ============================================
echo.

pause
endlocal
