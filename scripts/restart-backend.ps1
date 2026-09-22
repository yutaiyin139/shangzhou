$ErrorActionPreference = "SilentlyContinue"
$py = "C:\Users\yuty\AppData\Local\Programs\Python\Python313\python.exe"
$backendDir = "E:\VSCode-workspaces\shangzhou\backend"

# 停止旧 backend
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'app\.py' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Sleep -Seconds 2

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = "app.py"
$psi.WorkingDirectory = $backendDir
$psi.WindowStyle = 'Hidden'
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $true
$p = [System.Diagnostics.Process]::Start($psi)
Write-Host "backend started PID: $($p.Id)"
