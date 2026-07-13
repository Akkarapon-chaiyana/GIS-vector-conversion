@echo off
setlocal
rem Double-click this file to start the Vector Format Converter on Windows.
cd /d "%~dp0backend"

rem If the app is already running, just open the browser.
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/formats -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:8000
  echo Converter already running - opened http://localhost:8000
  timeout /t 3 >nul
  exit /b 0
)

rem Pick a Python launcher.
set "PY=python"
where py >nul 2>nul && set "PY=py -3"

rem First-time setup: create the environment and install dependencies.
if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating the Python environment, this takes a few minutes...
  %PY% -m venv .venv || goto :err
  ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :err
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :err
)

rem Open the browser once the server responds.
start "" /b powershell -NoProfile -Command "for ($i=0; $i -lt 60; $i++) { try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/formats -TimeoutSec 1 | Out-Null; Start-Process 'http://localhost:8000'; break } catch { Start-Sleep -Milliseconds 500 } }"

echo Starting Vector Format Converter at http://localhost:8000 (press Ctrl+C or close this window to stop)
".venv\Scripts\python.exe" -m uvicorn main:app --port 8000
exit /b 0

:err
echo.
echo Setup failed. Install Python 3.10+ from https://www.python.org/downloads/
echo (check "Add python.exe to PATH" in the installer), then run this file again.
pause
exit /b 1
