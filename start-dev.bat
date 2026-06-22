@echo off
REM ============================================================
REM start-dev.bat  -  Native DEV stack on ports 8001 / 3001.
REM
REM Runs alongside the Docker prod stack (8000/3000), sharing the host
REM Ollama + MongoDB. The LLM is served by Ollama, so nothing loads onto
REM the GPU here. Refuses to run on main/master.
REM
REM Run from the repo root after checking out your feature branch.
REM ============================================================
setlocal
cd /d %~dp0

REM Guard: this is the DEV launcher, not for the prod branch.
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if /I "%BRANCH%"=="main"   goto :onmain
if /I "%BRANCH%"=="master" goto :onmain

set PORT_BACKEND=8001
set PORT_FRONTEND=3001

REM Warn (don't fail) if Ollama isn't reachable.
netstat -ano | findstr ":11434 " | findstr LISTENING >nul
if errorlevel 1 echo [start-dev] WARNING: Ollama not detected on 11434 - LLM calls will fail until it is running.

REM Start MongoDB only if it isn't already up (shared with prod).
REM --bind_ip_all so the prod containers can reach it via host.docker.internal.
netstat -ano | findstr ":27017 " | findstr LISTENING >nul
if errorlevel 1 (
    echo [start-dev] Starting MongoDB...
    start "" mongod --dbpath "%~dp0data\db" --bind_ip_all
    timeout /t 3 >nul
) else (
    echo [start-dev] MongoDB already running, reusing it.
)

echo [start-dev] Backend on %PORT_BACKEND% ^(branch "%BRANCH%", reload^)...
start "" cmd /k "call env\Scripts\activate && cd /d %~dp0backend && uvicorn scripts.main:app --host 0.0.0.0 --port %PORT_BACKEND% --reload"

timeout /t 1 >nul

echo [start-dev] Frontend on %PORT_FRONTEND%...
start "" cmd /C "cd /d %~dp0frontend && set NEXT_PUBLIC_BACKEND_PORT=%PORT_BACKEND% && npm run dev -- -p %PORT_FRONTEND%"

echo [start-dev] Dev up:  frontend http://localhost:%PORT_FRONTEND%  /  backend http://localhost:%PORT_BACKEND%
goto :eof

:onmain
echo [start-dev] Refusing to run on "%BRANCH%" - this is the DEV launcher.
echo [start-dev] Switch to your feature branch first, e.g.:  git checkout dev
exit /b 1
