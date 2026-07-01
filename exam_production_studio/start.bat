@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo  出卷集成工作台 - 一键启动
echo ============================================

REM ---- backend venv and deps ----
if not exist ".venv\Scripts\python.exe" (
  echo [安装] 正在创建 Python 虚拟环境并安装后端依赖……
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
)

REM ---- backend deps: run every start so newly-added/missing deps are auto-installed ----
REM (pip skips already-satisfied packages quickly; only missing ones are downloaded)
echo [deps] checking backend dependencies (auto-install if missing) ...
.venv\Scripts\python -m pip install -q -r backend\requirements.txt

REM ---- frontend deps ----
if not exist "frontend\node_modules" (
  echo [安装] 正在安装前端依赖……
  pushd frontend
  call npm install
  popd
)

REM ---- ensure browser deps for 学科网 Cookie auto-fetch (login window / read browser) ----
.venv\Scripts\python -c "import playwright" 2>nul
if errorlevel 1 (
  echo [安装] 正在安装 playwright 与 browser_cookie3 ……
  .venv\Scripts\python -m pip install playwright browser_cookie3
)
REM install chromium engine (idempotent; fast no-op if already present)
.venv\Scripts\python -m playwright install chromium >nul 2>&1

REM ---- ensure LibreOffice (needed for in-app PDF template preview) ----
set "SOFFICE_PATH="
if exist "%ProgramFiles%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles%\LibreOffice\program\soffice.exe"
if not defined SOFFICE_PATH if exist "%ProgramFiles(x86)%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"
if not defined SOFFICE_PATH for /f "delims=" %%i in ('where soffice 2^>nul') do set "SOFFICE_PATH=%%i"
if not defined SOFFICE_PATH (
  echo [安装] 未找到 LibreOffice —— 应用内 PDF 模板预览需要它。
  where winget >nul 2>&1
  if errorlevel 1 (
    echo [安装] 系统无 winget，请手动安装 LibreOffice：https://www.libreoffice.org/download/
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_libreoffice.ps1"
    if exist "%ProgramFiles%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles%\LibreOffice\program\soffice.exe"
    if not defined SOFFICE_PATH if exist "%ProgramFiles(x86)%\LibreOffice\program\soffice.exe" set "SOFFICE_PATH=%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"
  )
)
if defined SOFFICE_PATH (
  echo [安装] 已找到 LibreOffice：%SOFFICE_PATH%
) else (
  echo [安装] 仍未检测到 LibreOffice；在安装前 PDF 预览将保持禁用。
)

echo [清理] 正在停止此前的后端/前端进程（含热重载子进程）……
REM Merged cleanup (kill uvicorn + vite + port listeners + wait) into a single
REM powershell process. Previously this was 4 separate powershell.exe launched
REM in quick succession; that burst could hit 0xc0000142 (STATUS_DLL_INIT_FAILED)
REM on a constrained desktop heap. One process = no burst.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\stop_servers.ps1" >nul 2>&1
REM also close previous EPS windows started by this script
taskkill /F /FI "WINDOWTITLE eq EPS Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq EPS Frontend*" >nul 2>&1

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
echo    [1] 热重载模式：修改后端代码后自动重启
echo    [2] 非热重载模式：稳定；修改后端代码后需重新运行启动脚本
echo ============================================
set "EPS_RELOAD="
set "MODE="
set /p "MODE=请输入 1 或 2，默认 2： "
if "%MODE%"=="1" (
  set "EPS_RELOAD=--reload"
  echo [模式] 已启用热重载
) else (
  echo [模式] 已禁用热重载，稳定模式
)

echo [运行] 后端 http://127.0.0.1:8000  前端 http://localhost:5173
REM backend: powershell -NoExit keeps the window open after a crash so the traceback stays visible;
REM Tee-Object also streams output into backend\backend.log for post-mortem.
start "EPS Backend" powershell -NoProfile -NoExit -Command "& '.venv\Scripts\python.exe' -m uvicorn main:app --app-dir backend --port 8000 %EPS_RELOAD% 2>&1 | Out-String -Stream | Tee-Object -FilePath 'backend\backend.log'"

REM Wait (max 60s) until backend /api/health responds before starting the
REM frontend, to avoid the startup race (vite proxy 500 / blank config page).
REM Single powershell with an internal loop = no powershell burst.
echo [WAIT] waiting for backend to be ready ...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(60); while((Get-Date) -lt $d){ try{ Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 | Out-Null; exit 0 }catch{ Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 echo [WARN] backend not detected within 60s; starting frontend anyway (refresh the page if it is blank).

start "EPS Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo 后端与前端已在两个新窗口中启动。
echo 请在浏览器打开：http://localhost:5173
echo 关闭这两个窗口，或在其中按 Ctrl+C，即可停止。
endlocal
