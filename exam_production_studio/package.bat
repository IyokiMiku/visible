@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ============================================================
REM  Pack a CLEAN source zip for another Windows machine.
REM  Excludes machine-specific / runtime dirs:
REM    .venv  node_modules  dist  __pycache__  .git
REM    data\projects  data\studio.db  .env  *.pyc
REM  On target machine: unzip, then run start.bat (first run
REM  auto-creates venv and installs deps; needs Python 3.10+,
REM  Node 18+ and internet for the first install).
REM ============================================================

set "STAGE=%TEMP%\eps_pkg_stage"
set "PKGNAME=exam_production_studio"
set "OUTZIP=%~dp0..\%PKGNAME%_src.zip"

echo [pack] staging clean copy ...
if exist "%STAGE%" rmdir /S /Q "%STAGE%"
mkdir "%STAGE%\%PKGNAME%"

robocopy "%~dp0." "%STAGE%\%PKGNAME%" /E ^
  /XD ".venv" "node_modules" "dist" "__pycache__" ".git" "projects" ^
  /XF "studio.db" ".env" "*.pyc" >nul

echo [pack] compressing to %OUTZIP% ...
if exist "%OUTZIP%" del /Q "%OUTZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%STAGE%\%PKGNAME%' -DestinationPath '%OUTZIP%' -Force"

rmdir /S /Q "%STAGE%"

echo.
echo [done] package created:
echo   %OUTZIP%
echo.
echo On the target Windows PC:
echo   1) install Python 3.10+ and Node 18+ (only once)
echo   2) unzip the package
echo   3) run %PKGNAME%\start.bat  (first run installs deps, needs internet)
echo.
endlocal
