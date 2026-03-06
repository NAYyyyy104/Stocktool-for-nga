@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo [StockToolForNga] Checking Docker CLI...
docker --version >nul 2>nul
if errorlevel 1 (
  echo [StockToolForNga] Docker CLI not found. Please install Docker Desktop first.
  pause
  exit /b 1
)

echo [StockToolForNga] Checking Docker daemon...
docker info >nul 2>nul
if errorlevel 1 (
  echo [StockToolForNga] Docker daemon is not running.
  echo Please start Docker Desktop, wait until it is ready, then run this script again.
  pause
  exit /b 1
)

set "PORT_PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8080 .*LISTENING"') do (
  set "PORT_PID=%%p"
  goto :port_checked
)
:port_checked
if defined PORT_PID (
  echo [StockToolForNga] Warning: port 8080 is already in use by PID !PORT_PID!.
  echo The web page may not be reachable at http://localhost:8080
)

set "ONLINE_UPDATE=%CGP_DOCKER_ONLINE%"
if /I "%ONLINE_UPDATE%"=="1" (
  echo [StockToolForNga] Online update mode enabled. Building images with pull...
  call :run_with_retry "docker compose build --pull" 2
  if errorlevel 1 (
    echo [StockToolForNga] Online pull failed. Falling back to local-cache build...
    call :run_with_retry "docker compose build" 2
    if errorlevel 1 goto :start_failed
  )
) else (
  echo [StockToolForNga] Offline-first mode. Building images from local cache...
  call :run_with_retry "docker compose build" 2
  if errorlevel 1 (
    echo [StockToolForNga] Local-cache build failed. Trying online pull as fallback...
    call :run_with_retry "docker compose build --pull" 1
    if errorlevel 1 goto :start_failed
  )
)

echo [StockToolForNga] Starting Docker services...
call :run_with_retry "docker compose up -d" 2
if errorlevel 1 goto :start_failed

echo [StockToolForNga] Started successfully.
echo Open http://localhost:8080 in your browser.
echo Tip: set CGP_DOCKER_ONLINE=1 if you want to force online image refresh.
pause
exit /b 0

:start_failed
echo [StockToolForNga] Failed to start services.
echo.
echo Possible causes:
echo 1. Temporary network issue when pulling base images from Docker Hub.
echo 2. Docker proxy/registry mirror not configured.
echo 3. Port conflict on 8080.
echo.
echo You can try:
echo - docker login
echo - docker compose pull
echo - docker compose build --pull --no-cache
echo - docker compose up -d
pause
exit /b 1

:run_with_retry
setlocal EnableDelayedExpansion
set "CMD=%~1"
set /a MAX_RETRY=%~2
if "%MAX_RETRY%"=="" set /a MAX_RETRY=2
set /a ATTEMPT=1

:retry_loop
echo [StockToolForNga] Running (!ATTEMPT!/!MAX_RETRY!): !CMD!
cmd /c "!CMD!"
if !errorlevel! equ 0 (
  endlocal
  exit /b 0
)
if !ATTEMPT! geq !MAX_RETRY! (
  endlocal
  exit /b 1
)
echo [StockToolForNga] Command failed. Retrying in 3 seconds...
timeout /t 3 /nobreak >nul
set /a ATTEMPT+=1
goto :retry_loop
