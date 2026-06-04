@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if exist "%CD%\runtime\python\python.exe" (
  set "PYTHON_EXE=%CD%\runtime\python\python.exe"
)
set "DATA_DIR=%CD%\backend\data"

echo.
echo Job profiling demo - reset demo scope
echo =====================================
echo This resets only demo users, demo campaigns, demo profiles and demo documents.
echo Work data with is_demo=false stays in backend\data\demo.sqlite.
echo.
set /p "CONFIRM=Type RESET and press Enter to continue: "
if /I not "%CONFIRM%"=="RESET" (
  echo Cancelled.
  exit /b 0
)

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python was not found:
  echo %PYTHON_EXE%
  pause
  exit /b 1
)

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

set "AI_MODE=off"
set "AI_PROVIDER=off"
set "APP_ENV=demo-local"
set "PROFILER_DATA_DIR=%DATA_DIR%"

set "PYTHONPATH=backend"
"%PYTHON_EXE%" -m app.reset_demo_cli
if errorlevel 1 (
  echo [ERROR] Demo reset failed.
  pause
  exit /b 1
)

echo.
echo [OK] Demo scope reset completed.
pause
exit /b 0
