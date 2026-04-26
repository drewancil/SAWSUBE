@echo off
REM SAWSUBE — Windows start script
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist .venv (
  echo Creating venv...
  python -m venv .venv || goto :error
)

call .venv\Scripts\activate.bat

echo Installing backend deps...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt || goto :error

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from template — edit and re-run if needed.
)

REM Build frontend if Node available and no dist
where node >nul 2>nul
if %errorlevel%==0 (
  if not exist frontend\dist (
    echo Building frontend...
    pushd frontend
    call npm install || goto :error
    call npm run build || goto :error
    popd
  )
) else (
  echo Node.js not found — frontend will not be served. API only.
)

REM ── Instance check ─────────────────────────────────────────────────────────
for /f "tokens=1" %%P in ('wmic process where "commandline like '%%backend.main%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
  set EXISTING_PID=%%P
)
if defined EXISTING_PID (
  echo.
  echo [WARNING] SAWSUBE is already running ^(PID: %EXISTING_PID%^)
  echo   [k] Kill existing instance and start fresh
  echo   [e] Exit without starting another
  set /p CHOICE="  Choice [k/e]: "
  if /i "!CHOICE!"=="k" (
    echo Stopping PID %EXISTING_PID%...
    taskkill /F /PID %EXISTING_PID% >nul 2>&1
    timeout /t 2 /nobreak >nul
  ) else (
    echo Exiting - existing instance left running.
    goto :eof
  )
)

echo Starting SAWSUBE on http://localhost:8000
python -m backend.main
goto :eof

:error
echo FAILED.
pause
exit /b 1
