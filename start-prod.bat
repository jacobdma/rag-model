@echo off
REM ============================================================
REM start-prod.bat  -  (Re)start the PROD stack WITHOUT redeploying.
REM
REM Brings up the last-built prod containers (rag-prod) using existing
REM images - no git checkout, no pull, no rebuild. Use this to recover
REM after a crash or reboot without deploying fresh code.
REM
REM To deploy new code from main instead, use deploy.bat.
REM Run from the repo root.
REM ============================================================
setlocal
cd /d %~dp0

REM Warn (don't fail) if Ollama isn't reachable.
netstat -ano | findstr ":11434 " | findstr LISTENING >nul
if errorlevel 1 echo [start-prod] WARNING: Ollama not detected on 11434 - LLM calls will fail until it is running.

REM A crash/reboot may have taken Mongo down too; start it if needed.
REM --bind_ip_all so the containers can reach it via host.docker.internal.
netstat -ano | findstr ":27017 " | findstr LISTENING >nul
if errorlevel 1 (
    echo [start-prod] Starting MongoDB...
    start "" mongod --dbpath "%~dp0data\db" --bind_ip_all
    timeout /t 3 >nul
) else (
    echo [start-prod] MongoDB already running.
)

echo [start-prod] Starting prod containers (last-built images, no rebuild)...
docker compose -p rag-prod up -d
if errorlevel 1 (
    echo [start-prod] Failed. If the images were never built, run deploy.bat first.
    exit /b 1
)
echo [start-prod] Prod up:  frontend http://localhost:3000  /  backend http://localhost:8000
endlocal
