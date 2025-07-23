@echo off
echo Starting MongoDB...
start "" mongod --dbpath "%~dp0data\db"

timeout /t 3 >nul

echo Starting Next.js frontend...
start "" cmd /k "cd /d %~dp0frontend && npm run dev"