@echo off
echo Starting Airtable LinkedIn URL Extractor - Full Stack Application
echo.

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
pip install fastapi uvicorn pydantic

echo.
echo Starting FastAPI Backend...
echo Backend will be available at: http://localhost:8080
echo API Documentation at: http://localhost:8080/docs
echo.

REM Start the backend in a new window with direct uvicorn command
start "FastAPI Backend" cmd /k "python -m uvicorn airtable_api:app --host 0.0.0.0 --port 8080 --reload --log-level info"

REM Wait a moment for the backend to start
timeout /t 3 /nobreak >nul

echo.
echo Starting React Frontend...
echo Frontend will be available at: http://localhost:3000
echo.

REM Navigate to frontend directory and start React
cd frontend
if not exist "node_modules" (
    echo Installing React dependencies...
    npm install
)

REM Start the frontend in a new window
start "React Frontend" cmd /k "npm start"

echo.
echo Both services are starting...
echo.
echo Backend:  http://localhost:8080
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8080/docs
echo.
echo Press any key to open the frontend in your browser...
pause >nul

REM Open the frontend in the default browser
start http://localhost:3000

echo.
echo Services are running! You can now use the web interface.
echo.
echo To stop the services, close the command windows that opened.
pause 