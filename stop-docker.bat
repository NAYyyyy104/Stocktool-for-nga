@echo off
cd /d "%~dp0"

echo [StockToolForNga] Stopping Docker services...
docker compose down

if %errorlevel% neq 0 (
  echo [StockToolForNga] Failed to stop services.
  pause
  exit /b 1
)

echo [StockToolForNga] Stopped.
pause
