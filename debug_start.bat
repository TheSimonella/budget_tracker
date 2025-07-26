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

:: Test if app.py exists
if not exist "app.py" (
    echo ERROR: app.py not found in current directory!
    echo.
    pause
    exit /b 1
)

:: Try to run the application
echo.
echo Starting Flask application...
echo If you see any errors below, please note them.
echo.

:: Run Python with full error output
python app.py

:: If we get here, the app stopped
echo.
echo ========================================
echo Application stopped or encountered an error.
echo Check the messages above for any errors.
echo ========================================
echo.
pause