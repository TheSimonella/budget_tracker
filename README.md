# Budget Tracker

Personal Budgeting App.

## Running the application on Windows

Use `start_budget_tracker.bat` to launch the app. The script will
automatically create a Python virtual environment if it doesn't exist,
install the dependencies from `requirements.txt`, and then start the
Flask server and open your browser.

## Debugging on Windows

For troubleshooting, you can run `debug_start.bat`. It assumes the virtual
environment already exists, verifies that Python 3.7+ and Flask are installed,
and sets `FLASK_ENV=development`, `FLASK_DEBUG=1` and `PYTHONFAULTHANDLER=1`.
The application is executed with detailed error output and all console logs
are captured in `debug.log` for later inspection. The window remains open so
you can review any issues.
