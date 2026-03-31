@echo off
setlocal
cd /d "%~dp0"

set "PORT=8010"
set "URL=http://127.0.0.1:%PORT%/"

if not exist ".venv\Scripts\python.exe" (
  echo The local virtual environment was not found.
  echo Please let Codex reinstall the dependencies for this project.
  pause
  exit /b 1
)

echo Starting Fantasy Football Team Creator on %URL%
start "Fantasy Football Team Creator Server" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%"

echo Waiting for local server...
powershell -NoProfile -Command "$url='%URL%'; $ready=$false; 1..20 | ForEach-Object { try { $response = Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 2; if ($response.StatusCode -eq 200) { $ready=$true; break } } catch { Start-Sleep -Milliseconds 500 } }; if (-not $ready) { exit 1 }"

if errorlevel 1 (
  echo The site did not become ready in time.
  echo Check the server window for the error message.
  pause
  exit /b 1
)

start "" "%URL%"
