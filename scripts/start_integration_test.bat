@echo off
REM Start Integration Point 5 Testing (Windows)

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "INTEGRATION_DIR=%PROJECT_ROOT%\integration"

echo ========================================
echo   Jarvis Integration Point 5 Testing
echo ========================================
echo.

REM Check virtual environment
if not exist "%PROJECT_ROOT%\.venv" (
    echo [ERROR] Virtual environment not found
    echo Please run setup first
    exit /b 1
)

REM Activate virtual environment
call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"

REM Check API Gateway
echo [INFO] Checking API Gateway...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] API Gateway not running. Please start it first:
    echo   cd api-gateway
    echo   uvicorn app.main:app --reload
    exit /b 1
)
echo [OK] API Gateway is running

REM Check Redis
echo [INFO] Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis not running
    echo Please start Redis first
    exit /b 1
)
echo [OK] Redis is running

REM Install dependencies
echo [INFO] Installing dependencies...
cd /d "%INTEGRATION_DIR%"
if exist requirements.txt (
    pip install -q -r requirements.txt
)

REM Create logs directory
if not exist "logs" mkdir logs

REM Parse arguments
set "SCENARIO=youtube"
if not "%~1"=="" set "SCENARIO=%~1"

set "REAL_SERVICES="
if

 not "%~2"=="" set "REAL_SERVICES=--use-real-services"

echo.
echo [INFO] Running Integration Test
echo   Scenario: %SCENARIO%
if defined REAL_SERVICES (
    echo   Mode: Real Services
) else (
    echo   Mode: Mock Services
)
echo.

REM Run test
python integration_test.py --scenario %SCENARIO% %REAL_SERVICES%

set EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
if %EXIT_CODE% equ 0 (
    echo [SUCCESS] Integration test passed!
) else (
    echo [FAILED] Integration test failed (code: %EXIT_CODE%^)
)
echo ========================================

exit /b %EXIT_CODE%
