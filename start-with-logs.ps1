# ============================================
# Shangzhou Smart Workbench - Start with Logs
# ============================================
# Redis/Qdrant/Celery run silently in background.
# Backend Flask and Frontend Vite each get their own
# visible terminal window for real-time log monitoring.
# ============================================

$ErrorActionPreference = "SilentlyContinue"

# ---------- Paths ----------
$RootDir     = $PSScriptRoot
$PythonPath  = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
if (-not (Test-Path $PythonPath)) { $PythonPath = "python" }

$BackendDir  = "$RootDir\backend"
$FrontendDir = "$RootDir\front"
$LogsDir     = "$RootDir\logs"

if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null }

# ---------- Silent background launcher ----------
function Start-Background {
    param([string]$WorkingDirectory, [string]$Command)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName         = "cmd.exe"
    $psi.Arguments        = "/c $Command"
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.WindowStyle      = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow   = $true
    $psi.UseShellExecute  = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
}

# ---------- Visible terminal launcher ----------
function Start-Visible {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd.HHmmss"
    $logFile    = "$LogsDir\$Title-$timestamp.log"

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName         = "cmd.exe"
    $psi.Arguments        = "/k `"echo [$Title] Log: $logFile`r`n$Command`""
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.WindowStyle      = [System.Diagnostics.ProcessWindowStyle]::Normal
    $psi.CreateNoWindow   = $false
    $psi.UseShellExecute  = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null

    Write-Host "  [OK] $Title terminal opened -> $logFile"
}

# ============================================
Write-Host ""
Write-Host "============================================"
Write-Host "  Shangzhou Workbench - Starting (log mode)"
Write-Host "============================================"
Write-Host ""

# ---------- Step 1: Redis ----------
Write-Host "[1/6] Redis (localhost:6379) ..."
$redisRunning = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if ($redisRunning) {
    Write-Host "  [OK] Redis already running"
} else {
    $redisExe = "$RootDir\Redis-8.10.1\redis-server.exe"
    if (Test-Path $redisExe) {
        Start-Background -WorkingDirectory "$RootDir\Redis-8.10.1" -Command "`"$redisExe`" --port 6379"
        Start-Sleep -Seconds 3
        $redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
        if ($redisPort) { Write-Host "  [OK] Redis started" } else { Write-Host "  [ERROR] Redis failed to start" }
    } else {
        Write-Host "  [WARN] redis-server.exe not found"
    }
}

# ---------- Step 2: Qdrant ----------
Write-Host "[2/6] Qdrant (localhost:6333) ..."
$qdrantRunning = Get-NetTCPConnection -LocalPort 6333 -State Listen -ErrorAction SilentlyContinue
if ($qdrantRunning) {
    Write-Host "  [OK] Qdrant already running"
} else {
    $qdrantExe = "$RootDir\qdrant\qdrant.exe"
    if (Test-Path $qdrantExe) {
        Start-Background -WorkingDirectory "$RootDir\qdrant" -Command "`"$qdrantExe`" --config-path `"$RootDir\qdrant\config\config.yaml`""
        Start-Sleep -Seconds 6
        $qdrantPort = Get-NetTCPConnection -LocalPort 6333 -State Listen -ErrorAction SilentlyContinue
        if ($qdrantPort) { Write-Host "  [OK] Qdrant started" } else { Write-Host "  [WARN] Qdrant may have failed to start" }
    } else {
        Write-Host "  [WARN] qdrant.exe not found"
    }
}

# ---------- Step 3: Backend Flask (visible) ----------
Write-Host "[3/6] Backend Flask (port 5000) - visible window ..."
$flaskPort = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($flaskPort) {
    Write-Host "  [OK] Backend already running (port 5000)"
} else {
    Start-Visible -Title "backend" -WorkingDirectory $BackendDir -Command "`"$PythonPath`" app.py 2>&1"
    Start-Sleep -Seconds 5
    $flaskPort = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($flaskPort) { Write-Host "  [OK] Backend started" } else { Write-Host "  [WARN] Backend may have failed, check log window" }
}

# ---------- Step 4: Frontend Vite (visible) ----------
Write-Host "[4/6] Frontend Vite (port 5173) - visible window ..."
$vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($vitePort) {
    Write-Host "  [OK] Frontend already running (port 5173)"
} else {
    if (-not (Test-Path "$FrontendDir\node_modules")) {
        Write-Host "  First run, installing frontend dependencies..."
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
    Start-Visible -Title "frontend" -WorkingDirectory $FrontendDir -Command "npm run dev 2>&1"
    Start-Sleep -Seconds 8
    $vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    if ($vitePort) { Write-Host "  [OK] Frontend started" } else { Write-Host "  [WARN] Frontend may have failed, check log window" }
}

# ---------- Step 5: Celery Worker ----------
Write-Host "[5/6] Celery Worker (background) ..."
$redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if (-not $redisPort) {
    Write-Host "  [WARN] Redis not running, Celery cannot start"
} else {
    $celeryRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*celery*worker*' }
    if ($celeryRunning) {
        Write-Host "  [OK] Celery Worker already running"
    } elseif (Test-Path "$BackendDir\tasks\celery_app.py") {
        Start-Background -WorkingDirectory $BackendDir -Command "`"$PythonPath`" -m celery -A tasks.celery_app worker --loglevel=info -Q workflow,embedding,scheduled"
        Start-Background -WorkingDirectory $BackendDir -Command "`"$PythonPath`" -m celery -A tasks.celery_app beat --loglevel=info"
        Write-Host "  [OK] Celery Worker + Beat started in background"
    } else {
        Write-Host "  [WARN] celery_app.py not found"
    }
}

# ---------- Step 6: Summary ----------
Write-Host ""
Write-Host "============================================"
Write-Host "  Startup Complete"
Write-Host "============================================"
Write-Host ""
Write-Host "  Frontend : http://localhost:5173"
Write-Host "  Backend  : http://localhost:5000"
Write-Host "  Redis   : localhost:6379"
Write-Host "  Logs    : $LogsDir"
Write-Host ""
Write-Host "  Tips:"
Write-Host "    - Ctrl+C in either window stops that service only"
Write-Host "    - Run stop-all.bat to stop everything"
Write-Host ""
Write-Host "============================================"
