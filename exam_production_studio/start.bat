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

REM ---- choose backend mode ----
REM 1 = hot reload (--reload): backend auto-restarts when you edit code under backend\.
REM 2 = no reload: stable mode, you re-run start.bat after editing backend code.
REM NOTE on Windows: --reload makes WatchFiles re-spawn python workers on every save. If the
REM interactive desktop heap is small/exhausted, a respawned worker can die at startup with
REM 0xc0000142 (STATUS_DLL_INIT_FAILED). The desktop heap has been enlarged (SharedSection
REM 2nd value 20480 -> 40960) so reload should be stable; if 0xc0000142 ever returns, use mode 2.
echo.
echo ============================================
echo  请选择后端启动模式：
echo    [1] 热重载  (--reload，修改代码后自动重启)
echo    [2] 非热重载  (稳定模式；修改后端代码后需重新运行 start.bat)
echo ============================================
set "EPS_RELOAD="
set "MODE="
set /p "MODE=请输入 1 或 2 (默认 2): "
if "%MODE%"=="1" (
  set "EPS_RELOAD=--reload"
  echo [模式] 已启用热重载
) else (
  echo [模式] 已禁用热重载 ^(稳定模式^)
)

echo [run] backend http://127.0.0.1:8000  frontend http://localhost:5173
REM backend: powershell -NoExit keeps the window open after a crash so the traceback stays visible;
REM Tee-Object also streams output into backend\backend.log for post-mortem.
start "EPS Backend" powershell -NoProfile -NoExit -Command "& '.venv\Scripts\python.exe' -m uvicorn main:app --app-dir backend --port 8000 %EPS_RELOAD% 2>&1 | Out-String -Stream | Tee-Object -FilePath 'backend\backend.log'"
start "EPS Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Backend and frontend started in two new windows.
echo Open: http://localhost:5173
echo Close those windows (or Ctrl+C inside them) to stop.
endlocal
