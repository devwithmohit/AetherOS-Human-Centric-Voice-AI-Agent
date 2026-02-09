@echo off
REM Run M2 -> M10 Integration Tests (Windows)

echo ==================================
echo M2 -^> M10 Integration Test Runner
echo ==================================
echo.

REM Check if Memory Service is running
echo 1. Checking Memory Service...
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% equ 0 (
    echo    [OK] Memory Service is running
) else (
    echo    [!] Memory Service not running!
    echo    Starting Memory Service...
    cd ..\memory-service
    docker-compose up -d
    cd ..\integration-tests
    timeout /t 5 /nobreak >nul
    echo    [OK] Memory Service started
)

echo.
echo 2. Installing Python dependencies...
pip install -q -r requirements.txt
echo    [OK] Dependencies installed

echo.
echo 3. Generating test audio samples...
python generate_test_audio.py
echo    [OK] Test audio generated

echo.
echo 4. Running integration tests...
echo.
pytest test_m2_m10_integration.py -v -s --tb=short

echo.
echo ==================================
echo Integration Tests Complete!
echo ==================================
