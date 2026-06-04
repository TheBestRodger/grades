@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "PORT=8010"
set "HOST=127.0.0.1"
set "URL=http://%HOST%:%PORT%"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "PYTHON_LABEL=local .venv"
if exist "%CD%\runtime\python\python.exe" (
  set "PYTHON_EXE=%CD%\runtime\python\python.exe"
  set "PYTHON_LABEL=bundled portable runtime"
)
set "DATA_DIR=%CD%\backend\data"
set "STDOUT_LOG=%DATA_DIR%\uvicorn.stdout.log"
set "STDERR_LOG=%DATA_DIR%\uvicorn.stderr.log"

echo.
echo Job profiling demo - start
echo ==========================
echo Folder: %CD%
echo URL: %URL%
echo.

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Demo Python was not found:
  echo %PYTHON_EXE%
  echo.
  echo A self-extracting portable package already includes runtime\python.
  echo The local Python environment is not prepared.
  echo On a new PC install Python 3.12 and run the setup commands from README.md.
  echo Do not rely on a .venv folder copied from another computer.
  echo.
  pause
  exit /b 1
)

"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, alembic" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] The local Python environment cannot start the demo backend.
  echo.
  echo A copied .venv may be linked to Python from another computer.
  echo Recreate .venv on this PC using the setup commands from README.md.
  echo.
  pause
  exit /b 1
)

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

if not exist "%CD%\frontend\dist\index.html" (
  echo [INFO] frontend\dist was not found. Trying to build it...
  where npm.cmd >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] npm.cmd was not found, and frontend\dist is missing.
    echo Run on the development machine: npm.cmd --prefix frontend run build
    echo Then copy the project folder again.
    echo.
    pause
    exit /b 1
  )
  npm.cmd --prefix frontend run build
  if errorlevel 1 (
    echo [ERROR] Failed to build frontend. See details above.
    echo.
    pause
    exit /b 1
  )
)

set "LISTENING_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "LISTENING_PID=%%P"
)

if defined LISTENING_PID (
  echo [INFO] Port %PORT% is already used by PID !LISTENING_PID!.
  if defined PROFILER_NO_BROWSER (
    echo [INFO] Browser opening skipped: %URL%
  ) else (
    echo Opening current demo URL: %URL%
    start "" "%URL%"
  )
  exit /b 0
)

set "AI_MODE=off"
set "AI_PROVIDER=off"
set "APP_ENV=demo-local"
set "PROFILER_DATA_DIR=%DATA_DIR%"

echo [INFO] Python: %PYTHON_LABEL%.
echo [INFO] AI_MODE=off, SQLite in backend\data.
echo [INFO] Starting server in this window.
echo [INFO] Keep this window open while showing the demo.
echo.

if defined PROFILER_NO_BROWSER (
  echo [OK] Browser opening skipped: %URL%
) else (
  echo [INFO] Opening browser: %URL%
  start "" "%URL%"
)
echo.
echo To stop the demo, press Ctrl+C in this window or run stop_demo.bat.
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --app-dir backend --host %HOST% --port %PORT% --log-level info 1>> "%STDOUT_LOG%" 2>> "%STDERR_LOG%"

echo.
echo [INFO] Demo server stopped.
pause
exit /b 0
