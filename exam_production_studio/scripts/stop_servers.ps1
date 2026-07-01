# Stop previously started backend/frontend processes before a fresh start.
# Merged into a single PowerShell process to avoid spawning a burst of
# powershell.exe (which could fail at startup with 0xc0000142 when the
# desktop heap is exhausted).
$ErrorActionPreference = 'SilentlyContinue'

# tree-kill uvicorn (reloader + worker + multiprocessing spawn child that holds the socket)
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'uvicorn main:app' } |
  ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null }

# tree-kill the frontend vite dev server
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'vite' } |
  ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null }

# fallback: tree-kill whoever still listens on 8000/5173
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { taskkill /F /T /PID $_ 2>$null | Out-Null }

# give the OS a moment to release sockets
Start-Sleep -Milliseconds 1500
