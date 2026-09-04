@echo off
REM Start the x402 server in a detached window that survives session cleanup
cd /d "%~dp0"
start "Verve x402 API" cmd /k ".venv\Scripts\python.exe -u -m uvicorn main:app --host 127.0.0.1 --port 8000"
echo Server starting in a separate window on http://127.0.0.1:8000
