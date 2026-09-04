@echo off
REM Verve Paywall API launcher
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    uv venv --python 3.11 .venv
    uv pip install --python .venv\Scripts\python.exe x402 fastapi uvicorn httpx "x402[evm]" python-dotenv
)

echo Starting Verve Paywall API on http://localhost:8000
echo Free check:   .venv\Scripts\python.exe test_client.py free
echo Paid demo:    set PAYER_PRIVATE_KEY=0x... then .venv\Scripts\python.exe test_client.py paid
echo.
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
