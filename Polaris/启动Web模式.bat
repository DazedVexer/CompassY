@echo off
chcp 65001 >nul
cd /d "d:\Agent Leraing\AI Project\Polaris\MaxProject"

REM Check if frontend is built
if not exist "web\dist\index.html" (
    echo [Polaris] First run: building frontend ^(may take a few minutes^)...
    cd web
    call npm install
    call npm run build
    cd ..
    echo [Polaris] Frontend build done!
    echo.
)

echo [Polaris] Starting server...
echo Waiting 3 seconds for server to be ready...
echo.

REM Start server in background
start "Polaris Server" py -m server.main

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Open browser
start http://localhost:8000

echo.
echo Server is running! Browser should open shortly.
echo Close this window or press Ctrl+C in the server window to stop.
pause
