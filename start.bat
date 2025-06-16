@echo off
echo Starting MongoDB...
start "" mongod --dbpath "%~dp0data\db"

timeout /t 3 >nul

echo Starting FastAPI backend...
start "" cmd /k "call env\Scripts\activate && cd /d %~dp0backend && uvicorn scripts.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 1 >nul

echo Starting Next.js frontend...
start "" cmd /k "cd /d %~dp0frontend && npm run dev"
