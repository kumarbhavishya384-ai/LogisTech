@echo off
echo ==========================================
echo    STARTING LOGISTECH-OPENENV SYSTEM
echo ==========================================
cd /d "%~dp0"

:: Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Install requirements
echo.
echo [1/3] CHECKING DEPENDENCIES...
pip install -r requirements.txt

:: Start the server in a new window
echo.
echo [2/3] LAUNCHING BACKEND SERVER...
start "LogisTech-OpenEnv Backend" cmd /k "python server.py"

:: Open the browser to the Frontend
echo.
echo [3/3] OPENING DASHBOARD UI...
timeout /t 5 /nobreak >nul
start http://localhost:7860/

echo.
echo SERVER RUNNING AT http://localhost:7860
echo ==========================================
pause
