$ErrorActionPreference = "SilentlyContinue"
# 位置无关：以脚本所在目录的上级作为项目根，backend 为其下 backend 目录
$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "C:\Program Files\Python313\python.exe" }
$logsDir = Join-Path $root "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

# 停止旧 worker / beat
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'celery|billiard' } |
  ForEach-Object {
    Write-Host "stopping PID $($_.ProcessId): $($_.CommandLine.Substring(0, [Math]::Min(80, $_.CommandLine.Length)))..."
    Stop-Process -Id $_.ProcessId -Force
  }

Start-Sleep -Seconds 2

# 启动 worker / beat（Windows 下 celery_app.py 已自动选用 solo 池；日志落盘便于排查）
$workerCmd = "`"$py`" -m celery -A tasks.celery_app worker --loglevel=info -Q workflow,embedding,scheduled"
$beatCmd = "`"$py`" -m celery -A tasks.celery_app beat --loglevel=info"
Start-Process -FilePath $env:ComSpec -ArgumentList "/c", $workerCmd, ">`"$logsDir\celery-worker.log`" 2>&1`"" `
  -WorkingDirectory $backendDir -WindowStyle Hidden
Start-Process -FilePath $env:ComSpec -ArgumentList "/c", $beatCmd, ">`"$logsDir\celery-beat.log`" 2>&1`"" `
  -WorkingDirectory $backendDir -WindowStyle Hidden
Write-Host "worker + beat started, logs -> $logsDir\celery-worker.log / celery-beat.log"
