# ============================================
# Shangzhou Smart Workbench - Stop All Services (PowerShell)
# ============================================

param(
    [switch]$KeepRedis,
    [switch]$KeepQdrant,
    [switch]$Force
)

$ErrorActionPreference = "SilentlyContinue"

# Paths
$RedisDir = "$PSScriptRoot\Redis-8.10.1"
$RedisCli = "$RedisDir\redis-cli.exe"

$StopCount = 0
$FailCount = 0

function Stop-PortOwner {
    # Terminate whatever owns $Port and then RE-CHECK the port. Older code trusted
    # Stop-Process with -ErrorAction SilentlyContinue and always printed [OK], so a
    # denied kill looked like a clean shutdown; start-services then skipped the busy
    # port and the new code never got loaded.
    param([int]$Port, [string]$Name)

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) {
        Write-Host "  [SKIP] $Name not running (:$Port)"
        return
    }
    $ownerPid = ($conn | Select-Object -First 1).OwningProcess
    Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $after = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($after -and ($after | Select-Object -First 1).OwningProcess -eq $ownerPid) {
        Write-Host "  [FAIL] $Name (PID $ownerPid) still listening on :$Port - termination was denied"
        Write-Host "         Stop it from its own console, or rerun this script elevated."
        $script:FailCount++
        return
    }
    Write-Host "  [OK] $Name stopped"
    $script:StopCount++
}

Write-Host ""
Write-Host "============================================"
Write-Host "  Shangzhou Smart Workbench - Stop All"
Write-Host "============================================"
Write-Host ""

# ============================================
# Step 1: Stop Celery Worker
# ============================================
Write-Host "[1/5] Stopping Celery Worker + Beat..."

$celeryProcesses = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*celery*' }
if ($celeryProcesses) {
    $celeryProcesses | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    $celeryLeft = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*celery*' }
    if ($celeryLeft) {
        Write-Host "  [FAIL] Celery still running (PID $(($celeryLeft | Select-Object -ExpandProperty ProcessId) -join ', ')) - termination was denied"
        $FailCount++
    } else {
        Write-Host "  [OK] Celery Worker + Beat stopped"
        $StopCount++
    }
} else {
    Write-Host "  [SKIP] Celery Worker not running"
}

# ============================================
# Step 2: Stop Vite Frontend
# ============================================
Write-Host "[2/5] Stopping Frontend (Vite:5173) ..."

Stop-PortOwner -Port 5173 -Name "Frontend (Vite)"

# Also kill any remaining node processes related to vite
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like '*vite*' -or $_.CommandLine -like '*vite*'
} | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# ============================================
# Step 3: Stop Flask Backend
# ============================================
Write-Host "[3/5] Stopping Backend (Flask:5000) ..."

Stop-PortOwner -Port 5000 -Name "Backend (Flask)"

# ============================================
# Step 4: Stop Qdrant
# ============================================
Write-Host "[4/5] Stopping Qdrant (localhost:6333) ..."

if ($KeepQdrant) {
    Write-Host "  [SKIP] Keeping Qdrant (-KeepQdrant)"
} else {
    Stop-PortOwner -Port 6333 -Name "Qdrant"
}

# ============================================
# Step 5: Stop Redis
# ============================================
Write-Host "[5/5] Stopping Redis (localhost:6379) ..."

if ($KeepRedis) {
    Write-Host "  [SKIP] Keeping Redis (-KeepRedis)"
} else {
    # Try graceful shutdown first
    if (Test-Path $RedisCli) {
        & $RedisCli shutdown nosave 2>$null
        Start-Sleep -Seconds 2
    }

    Stop-PortOwner -Port 6379 -Name "Redis"
}

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "============================================"

if ($StopCount -gt 0) {
    Write-Host "  Status: [Stopped $StopCount service(s)]"
} else {
    Write-Host "  Status: [Nothing to stop]"
}

if ($FailCount -gt 0) {
    Write-Host "  WARNING: $FailCount service(s) could NOT be stopped - they are still holding their ports."
}

Write-Host ""
Write-Host " Tips:"
Write-Host "  - Start services:     start-all.bat"
Write-Host "  - Stop frontend only: stop-front.bat"
Write-Host "  - Stop backend only:  stop-backend.bat"
Write-Host "  - Health check:       check-health.bat"
Write-Host ""

# Non-zero exit code so callers can tell a partial stop from a clean one.
# ($ExitCode is just an ordinary variable in PowerShell; only `exit` sets the code.)
if ($FailCount -gt 0) { exit 1 }
