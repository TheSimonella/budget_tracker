@echo off
echo Starting Budget Tracker...
echo.

:: Change to the budget-tracker directory
cd /d %~dp0

:: --------------------------------------------------------------------
:: Setup virtual environment if it does not already exist
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install required packages every run ensures dependencies are met
echo Installing dependencies...
pip install -r requirements.txt >nul

:: --------------------------------------------------------------------
:: Start the Flask application in the background
echo Starting Flask application...
echo.
echo Budget Tracker is starting up...
echo.

:: Run the application in a new window
start /min cmd /c "python app.py"

:: Wait a few seconds for the server to start
echo Waiting for server to start...
timeout /t 3 /nobreak > nul

:: Open in default browser
echo Opening Budget Tracker in your browser...
start http://localhost:5000

echo.
echo Budget Tracker is now running!
echo.
echo Access it at:
echo   - From this computer: http://localhost:5000
echo   - From your phone (on same WiFi), find your IP using 'ipconfig'
echo.
echo To stop the application, close the Flask window or press Ctrl+C in it.
echo.
echo This window will close in 10 seconds...
timeout /t 10