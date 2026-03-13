@echo off
echo ===================================================
echo Starting Synapse AI Agent (Backend ^& Frontend)
echo ===================================================

echo [1/2] Starting FastAPI Backend...
if exist .venv\Scripts\activate.bat (
    start "Synapse AI Backend" cmd /k "call .venv\Scripts\activate.bat && python main.py"
) else (
    start "Synapse AI Backend" cmd /k "uv run main.py"
)

echo [2/2] Starting React Frontend...
cd frontend
start "Synapse AI Frontend" cmd /k "npm run dev"
cd ..

echo.
echo Both services are starting up in separate windows!
echo - Backend will be available at http://localhost:8000
echo - Frontend will be available at http://localhost:5173
echo.
echo Opening browser to http://localhost:5173...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo You can close this window at any time. The services will continue running in their respective command windows.
pause
