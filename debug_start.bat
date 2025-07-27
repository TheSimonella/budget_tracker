@echo off
echo ========================================
echo Budget Tracker - Debug Mode
echo ========================================
echo.

:: Change to the budget-tracker directory
cd /d %~dp0
echo Current directory: %CD%
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first with: python -m venv venv
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: --------------------------------------------------------------------
:: Verify Python version is >= 3.7
echo.
echo Checking Python version...
python -c "import sys; print('Python version:', sys.version)"
python -c "import sys; exit(sys.version_info<(3,7))"
if errorlevel 1 (
    echo ERROR: Python 3.7 or higher is required!
    pause
    exit /b 1
)


:: Check if activation worked
where python
echo.

:: Check if required packages are installed
echo Checking installed packages...
pip list | findstr Flask
if errorlevel 1 (
    echo.
    echo ERROR: Flask not installed!
    echo Installing requirements...
    pip install -r requirements.txt
)

:: --------------------------------------------------------------------
:: Set debug environment variables
set FLASK_ENV=development
set FLASK_DEBUG=1
set PYTHONFAULTHANDLER=1
echo Debugging environment enabled.


:: Test if app.py exists
if not exist "app.py" (
    echo ERROR: app.py not found in current directory!
    echo.
    pause
    exit /b 1
)

:: Check for existing database file
if exist "budget_tracker.db" (
    echo Found database file: budget_tracker.db
) else (
    echo No database file found. It will be created on first run.
)

:: Try to run the application
echo.
echo Starting Flask application...
echo If you see any errors below, please note them.
echo.

:: Run Python with debug logging
set DEBUG_LOG=debug.log
echo Debug output will be logged to %DEBUG_LOG%
powershell -Command "python -X faulthandler app.py 2>&1 | Tee-Object -FilePath '%DEBUG_LOG%'"

:: If we get here, the app stopped
echo.
echo ========================================
echo Application stopped or encountered an error.
echo Check the messages above for any errors.
echo ========================================
echo.
pause