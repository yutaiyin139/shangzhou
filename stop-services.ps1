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
        if ($Force) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        } else {
            Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] Celery Worker + Beat stopped"
    $StopCount++
} else {
    Write-Host "  [SKIP] Celery Worker not running"
}

# ============================================
# Step 2: Stop Vite Frontend
# ============================================
Write-Host "[2/5] Stopping Frontend (Vite:5173) ..."

$vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($vitePort) {
    Stop-Process -Id $vitePort.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Frontend stopped"
    $StopCount++
} else {
    Write-Host "  [SKIP] Frontend not running"
}

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

$flaskPort = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($flaskPort) {
    Stop-Process -Id $flaskPort.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Backend stopped"
    $StopCount++
} else {
    Write-Host "  [SKIP] Backend not running"
}

# ============================================
# Step 4: Stop Qdrant
# ============================================
Write-Host "[4/5] Stopping Qdrant (localhost:6333) ..."

if ($KeepQdrant) {
    Write-Host "  [SKIP] Keeping Qdrant (-KeepQdrant)"
} else {
    $qdrantPort = Get-NetTCPConnection -LocalPort 6333 -State Listen -ErrorAction SilentlyContinue
    if ($qdrantPort) {
        Stop-Process -Id $qdrantPort.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Qdrant stopped"
        $StopCount++
    } else {
        Write-Host "  [SKIP] Qdrant not running"
    }
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

    $redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
    if ($redisPort) {
        Stop-Process -Id $redisPort.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Redis stopped"
        $StopCount++
    } else {
        Write-Host "  [SKIP] Redis not running"
    }
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

Write-Host ""
Write-Host " Tips:"
Write-Host "  - Start services:     start-all.bat"
Write-Host "  - Stop frontend only: stop-front.bat"
Write-Host "  - Stop backend only:  stop-backend.bat"
Write-Host "  - Health check:       check-health.bat"
Write-Host ""
