@echo off
setlocal EnableExtensions

set "APP_FOLDER=ProfilirovanieDemo"
set "PAYLOAD=%~dp0ProfilirovanieDemo_payload.zip"

if defined PROFILER_INSTALL_DIR (
  set "TARGET=%PROFILER_INSTALL_DIR%"
) else (
  for /f "usebackq delims=" %%D in (`powershell.exe -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
  set "TARGET=%DESKTOP%\%APP_FOLDER%"
  if exist "%TARGET%" set "TARGET=%DESKTOP%\%APP_FOLDER%_new"
)

echo.
echo Job profiling demo - portable extraction
echo =========================================
echo Destination: %TARGET%
echo.

if not exist "%TARGET%" mkdir "%TARGET%"
set "PORTABLE_PAYLOAD=%PAYLOAD%"
set "PORTABLE_TARGET=%TARGET%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath $env:PORTABLE_PAYLOAD -DestinationPath $env:PORTABLE_TARGET -Force"
if errorlevel 1 (
  echo [ERROR] Could not unpack the portable demo.
  pause
  exit /b 1
)

echo [OK] Portable demo was unpacked.

if defined PROFILER_NO_AUTOSTART (
  echo [INFO] Automatic start skipped.
  exit /b 0
)

start "" "%TARGET%"
start "" "%TARGET%\start_demo.bat"
exit /b 0
