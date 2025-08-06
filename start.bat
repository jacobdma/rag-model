@echo off
REM Usage: start.bat [BACKEND_PORT] [FRONTEND_PORT] [-r]
REM Example: start.bat 8000 3000 -r

set PORT_BACKEND=%1
set PORT_FRONTEND=%2
set RELOAD_FLAG=%3

REM Set default ports if not provided
if "%PORT_BACKEND%"=="" set PORT_BACKEND=8000
if "%PORT_FRONTEND%"=="" set PORT_FRONTEND=3000

REM Set reload option for FastAPI if -r flag is provided
set RELOAD_OPT=
if /I "%RELOAD_FLAG%"=="-r" set RELOAD_OPT=--reload

echo Starting MongoDB...
start "" mongod --dbpath "%~dp0data\db"

timeout /t 3 >nul

echo Starting FastAPI on port %PORT_BACKEND%...
start "" cmd /k "call env\Scripts\activate && cd /d %~dp0backend && uvicorn scripts.main:app --host 0.0.0.0 --port %PORT_BACKEND% %RELOAD_OPT%"

timeout /t 1 >nul

echo Starting Next.js frontend on port %PORT_FRONTEND%...
start "" cmd /k "cd /d %~dp0frontend && npm run dev -- -p %PORT_FRONTEND%"