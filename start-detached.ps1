# Helper script to start a process truly detached
param(
    [string]$WorkingDirectory,
    [string]$Command
)

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = "/c $Command"
$psi.WorkingDirectory = $WorkingDirectory
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $true
[System.Diagnostics.Process]::Start($psi) | Out-Null
