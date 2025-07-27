@echo off
echo Emergency Restart - Shutting down and restarting services
echo.

REM Kill all Python processes (except this script)
echo Stopping all Python processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

REM Kill Node.js processes (React development server)
echo Stopping Node.js processes...
taskkill /f /im node.exe >nul 2>&1

REM Kill any remaining processes on the ports we use
echo Stopping processes on ports 8080 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /f /pid %%a >nul 2>&1

echo.
echo All services stopped. Waiting 3 seconds before restarting...
timeout /t 3 /nobreak >nul

echo.
echo Starting services...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1

echo.
echo Starting FastAPI Backend...
echo Backend will be available at: http://localhost:8080
echo API Documentation at: http://localhost:8080/docs
echo.

REM Start the backend in a new window
start "FastAPI Backend" cmd /k "python -m uvicorn airtable_api:app --host 0.0.0.0 --port 8080 --reload --log-level info"

REM Wait a moment for the backend to start
timeout /t 5 /nobreak >nul

echo.
echo Starting React Frontend...
echo Frontend will be available at: http://localhost:3000
echo.

REM Navigate to frontend directory and start React
cd frontend
if not exist "node_modules" (
    echo Installing React dependencies...
    npm install >nul 2>&1
)

REM Start the frontend in a new window
start "React Frontend" cmd /k "npm start"

echo.
echo Services are restarting...
echo.
echo Backend:  http://localhost:8080
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8080/docs
echo.
echo Emergency restart completed!
echo.
pause 