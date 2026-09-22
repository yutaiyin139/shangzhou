# ============================================
# Shangzhou Smart Workbench - Start All Services (PowerShell)
# ============================================

$ErrorActionPreference = "SilentlyContinue"

# Paths
$PythonPath = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
if (-not (Test-Path $PythonPath)) { $PythonPath = "python" }

$RedisDir = "$PSScriptRoot\Redis-8.10.1"
$RedisExe = "$RedisDir\redis-server.exe"

$QdrantDir = "$PSScriptRoot\qdrant"
$QdrantExe = "$QdrantDir\qdrant.exe"
$QdrantConf = "$QdrantDir\config\config.yaml"

$BackendDir = "$PSScriptRoot\backend"
$FrontendDir = "$PSScriptRoot\front"

$ErrCount = 0
$WarnCount = 0

# Helper: start a process truly detached using .NET Process.Start with UseShellExecute
function Start-DetachedProcess {
    param(
        [string]$WorkingDirectory,
        [string]$Command
    )
    # Native .exe (Redis, Qdrant) must be launched directly: when wrapped in
    # "cmd.exe /c" with a hidden console (qdrant 1.19), the child is killed
    # silently right after startup and leaves no log, so start-all reports a
    # false "failed to start". Non-exe commands (python app.py, npm run dev,
    # celery) still need the cmd wrapper.
    if ($Command -match '^"([^"]+\.exe)"\s*(.*)$') {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Matches[1]
        $psi.Arguments = $Matches[2]
        $psi.WorkingDirectory = $WorkingDirectory
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        $psi.CreateNoWindow = $true
        $psi.UseShellExecute = $true
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        return
    }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c $Command"
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
}

Write-Host ""
Write-Host "============================================"
Write-Host "  Shangzhou Smart Workbench - Starting"
Write-Host "============================================"
Write-Host ""

# ============================================
# Step 1: Start Redis
# ============================================
Write-Host "[1/6] Starting Redis (localhost:6379) ..."

$redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if ($redisPort) {
    Write-Host "  [OK] Redis already running"
} elseif (Test-Path $RedisExe) {
    Start-DetachedProcess -WorkingDirectory $RedisDir -Command "`"$RedisExe`" --port 6379"
    Start-Sleep -Seconds 3
    $redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
    if ($redisPort) {
        Write-Host "  [OK] Redis started"
    } else {
        Write-Host "  [ERROR] Redis failed to start"
        $ErrCount++
    }
} else {
    Write-Host "  [WARN] Redis server binary not found"
    $WarnCount++
}

# ============================================
# Step 2: Start Qdrant
# ============================================
Write-Host "[2/6] Starting Qdrant (localhost:6333) ..."

$qdrantPort = Get-NetTCPConnection -LocalPort 6333 -State Listen -ErrorAction SilentlyContinue
if ($qdrantPort) {
    Write-Host "  [OK] Qdrant already running"
} elseif (Test-Path $QdrantExe) {
    Start-DetachedProcess -WorkingDirectory $QdrantDir -Command "`"$QdrantExe`" --config-path `"$QdrantConf`""
    Start-Sleep -Seconds 6
    $qdrantPort = Get-NetTCPConnection -LocalPort 6333 -State Listen -ErrorAction SilentlyContinue
    if ($qdrantPort) {
        Write-Host "  [OK] Qdrant started"
    } else {
        Write-Host "  [WARN] Qdrant may have failed to start"
        $WarnCount++
    }
} else {
    Write-Host "  [WARN] Qdrant server binary not found"
    $WarnCount++
}

# ============================================
# Step 3: Start Flask Backend
# ============================================
Write-Host "[3/6] Starting Backend (Flask:5000) ..."

$flaskPort = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($flaskPort) {
    Write-Host "  [OK] Backend already running (port 5000)"
} elseif (Test-Path "$BackendDir\app.py") {
    Start-DetachedProcess -WorkingDirectory $BackendDir -Command "`"$PythonPath`" app.py"
    Start-Sleep -Seconds 5
    $flaskPort = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($flaskPort) {
        Write-Host "  [OK] Backend started"
    } else {
        Write-Host "  [WARN] Backend may have failed to start. Check port 5000."
        $WarnCount++
    }
} else {
    Write-Host "  [ERROR] backend\app.py not found"
    $ErrCount++
}

# ============================================
# Step 4: Start Vite Frontend
# ============================================
Write-Host "[4/6] Starting Frontend (Vite:5173) ..."

$vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($vitePort) {
    Write-Host "  [OK] Frontend already running (port 5173)"
} elseif (Test-Path "$FrontendDir\package.json") {
    # Install dependencies if needed
    if (-not (Test-Path "$FrontendDir\node_modules")) {
        Write-Host "  First run, installing frontend dependencies..."
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
    Start-DetachedProcess -WorkingDirectory $FrontendDir -Command "npm run dev"
    Start-Sleep -Seconds 8
    $vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    if ($vitePort) {
        Write-Host "  [OK] Frontend started"
    } else {
        Write-Host "  [WARN] Frontend may have failed to start. Check port 5173."
        $WarnCount++
    }
} else {
    Write-Host "  [WARN] front\package.json not found"
    $WarnCount++
}

# ============================================
# Step 5: Start Celery Worker
# ============================================
Write-Host "[5/6] Starting Celery Worker ..."

$redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if (-not $redisPort) {
    Write-Host "  [WARN] Redis not running, Celery Worker cannot start"
    $WarnCount++
} else {
    $celeryRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*celery*worker*' }
    if ($celeryRunning) {
        Write-Host "  [OK] Celery Worker already running"
    } elseif (Test-Path "$BackendDir\tasks\celery_app.py") {
        Start-DetachedProcess -WorkingDirectory $BackendDir -Command "`"$PythonPath`" -m celery -A tasks.celery_app worker --loglevel=info -Q workflow,embedding,scheduled"
        Start-DetachedProcess -WorkingDirectory $BackendDir -Command "`"$PythonPath`" -m celery -A tasks.celery_app beat --loglevel=info"
        Start-Sleep -Seconds 4
        Write-Host "  [OK] Celery Worker + Beat started"
    } else {
        Write-Host "  [WARN] backend\tasks\celery_app.py not found"
        $WarnCount++
    }
}

# ============================================
# Step 6: Summary
# ============================================
Write-Host "[6/6] Summary"
Write-Host ""
Write-Host "============================================"

if ($ErrCount -gt 0) {
    Write-Host "  Status: [PARTIAL FAIL] - $ErrCount error(s), $WarnCount warning(s)"
} elseif ($WarnCount -gt 0) {
    Write-Host "  Status: [PARTIAL WARN] - $WarnCount warning(s)"
} else {
    Write-Host "  Status: [ALL OK]"
}

Write-Host ""
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:5000"
Write-Host "  Redis:    localhost:6379"
Write-Host "  Qdrant:   localhost:6333"
Write-Host "  Worker:   Celery async task queue"
Write-Host ""
Write-Host "============================================"
Write-Host ""
Write-Host " Tips:"
Write-Host "  - Stop all services: stop-all.bat"
Write-Host "  - Health check:      check-health.bat"
Write-Host ""
