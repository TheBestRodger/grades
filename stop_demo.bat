@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PORT=8010"
set "PIDS="

echo.
echo Job profiling demo - stop
echo =========================

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "PIDS=!PIDS! %%P"
)

if not defined PIDS (
  echo [INFO] Nothing is listening on port %PORT%.
  exit /b 0
)

echo Found process IDs:%PIDS%
echo.
set /p "CONFIRM=Stop these processes? Type Y and press Enter: "
if /I not "%CONFIRM%"=="Y" (
  echo Cancelled.
  exit /b 0
)

for %%P in (%PIDS%) do (
  echo [INFO] Stopping PID %%P...
  taskkill /PID %%P /F >nul 2>nul
)

echo [OK] Demo stopped.
exit /b 0
