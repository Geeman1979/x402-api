@echo off
REM Opens the wallet settings file in Notepad
cd /d "%~dp0"
echo Opening wallet settings... edit the WALLET_ADDRESS line, then save and close.
notepad ".env"
echo.
echo Done! Close this window.
pause
