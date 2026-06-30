@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo  Exam Production Studio - one-click start
echo ============================================

REM ---- backend venv and deps ----
if not exist ".venv\Scripts\python.exe" (
  echo [setup] creating Python venv and installing backend deps...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r backend\requirements.txt
)

REM ---- frontend deps ----
if not exist "frontend\node_modules" (
  echo [setup] installing frontend deps...
  pushd frontend
  call npm install
  popd
)

echo [cleanup] stopping previous backend/frontend (incl. reload child processes) ...
REM tree-kill uvicorn (reloader + worker + multiprocessing spawn child that holds the socket)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn main:app' } | ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null }" >nul 2>&1
REM tree-kill the frontend vite dev server
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'vite' } | ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null }" >nul 2>&1
REM fallback: tree-kill whoever still listens on 8000/5173
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { taskkill /F /T /PID $_ 2>$null | Out-Null }" >nul 2>&1
REM also close previous EPS windows started by this script
taskkill /F /FI "WINDOWTITLE eq EPS Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq EPS Frontend*" >nul 2>&1
REM give the OS a moment to release sockets
powershell -NoProfile -Command "Start-Sleep -Milliseconds 1500" >nul 2>&1

echo [run] backend http://127.0.0.1:8000  frontend http://localhost:5173
start "EPS Backend" .venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8000 --reload
start "EPS Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Backend and frontend started in two new windows.
echo Open: http://localhost:5173
echo Close those windows (or Ctrl+C inside them) to stop.
endlocal
