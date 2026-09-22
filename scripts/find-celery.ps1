Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Select-Object ProcessId, @{N='CL';E={$_.CommandLine}} |
  Where-Object { $_.CL -match 'celery|beat|app.py' } |
  Format-Table -Wrap -AutoSize
