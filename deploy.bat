@echo off
REM ============================================================
REM deploy.bat  -  Build & run the PROD stack (Docker) from main.
REM
REM Prod runs as containers built from main's code, so it's an immutable,
REM restart-surviving artifact: switching branches in your working tree can't
REM disturb it. Mongo + Ollama stay on the host; the containers are CPU-only
REM clients. Dev keeps running natively on 8001/3001 alongside it.
REM
REM Run from the repo root.
REM ============================================================
setlocal
cd /d %~dp0

REM Protect uncommitted dev work: refuse to deploy from a dirty tree.
set DIRTY=
for /f "delims=" %%i in ('git status --porcelain') do set DIRTY=1
if defined DIRTY (
    echo [deploy] Working tree is dirty. Commit or stash before deploying.
    exit /b 1
)

REM Remember the current branch so we can return to it after building.
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set PREV=%%b

echo [deploy] Switching to main and pulling...
git checkout main || (echo [deploy] checkout main failed & exit /b 1)
git pull --ff-only origin main || (echo [deploy] pull failed - resolve manually & git checkout %PREV% & exit /b 1)

echo [deploy] Building and starting prod containers...
docker compose -p rag-prod up -d --build
set RC=%ERRORLEVEL%

echo [deploy] Returning to branch "%PREV%"...
git checkout %PREV%

if not "%RC%"=="0" (
    echo [deploy] docker compose failed ^(exit %RC%^).
    exit /b %RC%
)
echo [deploy] Prod is up:  frontend http://localhost:3000  /  backend http://localhost:8000
endlocal
