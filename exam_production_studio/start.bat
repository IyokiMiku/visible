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

REM ---- ensure LibreOffice (needed for in-app PDF template preview) ----
set "SOFFICE_PATH="
if exist "%ProgramFiles%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles%\LibreOffice\program\soffice.exe"
if not defined SOFFICE_PATH if exist "%ProgramFiles(x86)%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"
if not defined SOFFICE_PATH for /f "delims=" %%i in ('where soffice 2^>nul') do set "SOFFICE_PATH=%%i"
if not defined SOFFICE_PATH (
  echo [setup] LibreOffice not found - it is required for the in-app PDF template preview.
  where winget >nul 2>&1
  if errorlevel 1 (
    echo [setup] winget unavailable. Please install LibreOffice manually: https://www.libreoffice.org/download/
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_libreoffice.ps1"
    if exist "%ProgramFiles%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles%\LibreOffice\program\soffice.exe"
    if not defined SOFFICE_PATH if exist "%ProgramFiles(x86)%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"
  )
)
if defined SOFFICE_PATH (
  echo [setup] LibreOffice: %SOFFICE_PATH%
) else (
  echo [setup] LibreOffice still not detected; PDF preview stays disabled until it is installed.
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
REM backend: powershell -NoExit keeps the window open after a crash so the traceback stays visible;
REM Tee-Object also streams output into backend\backend.log for post-mortem.
start "EPS Backend" powershell -NoProfile -NoExit -Command "& '.venv\Scripts\python.exe' -m uvicorn main:app --app-dir backend --port 8000 --reload 2>&1 | Out-String -Stream | Tee-Object -FilePath 'backend\backend.log'"
start "EPS Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Backend and frontend started in two new windows.
echo Open: http://localhost:5173
echo Close those windows (or Ctrl+C inside them) to stop.
endlocal
