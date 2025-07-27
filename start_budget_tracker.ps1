# Budget Tracker Startup Script

Write-Host "Starting Budget Tracker..." -ForegroundColor Green
Write-Host ""

# Get the script's directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptPath

# -----------------------------------------------------------------------
# Setup virtual environment if needed
if (!(Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install required packages
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt | Out-Null

# Get computer's IP address for network access
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"}).IPAddress | Select-Object -First 1

# Start the Flask application in background
Write-Host ""
Write-Host "Starting Flask application..." -ForegroundColor Yellow

# Start Flask in a new process
$flaskProcess = Start-Process python -ArgumentList "app.py" -PassThru -WindowStyle Minimized

# Wait for the server to start
Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Open in default browser
Write-Host "Opening Budget Tracker in your browser..." -ForegroundColor Green
Start-Process "http://localhost:5000"

# Display access information
Write-Host ""
Write-Host "Budget Tracker is now running!" -ForegroundColor Green
Write-Host ""
Write-Host "Access the application at:" -ForegroundColor Cyan
Write-Host "  - From this computer: http://localhost:5000" -ForegroundColor White
Write-Host "  - From your phone/tablet (same WiFi): http://${ipAddress}:5000" -ForegroundColor White
Write-Host ""
Write-Host "The Flask server is running in a minimized window." -ForegroundColor Yellow
Write-Host "To stop the application, close the Flask window or press Ctrl+C in it." -ForegroundColor Yellow
Write-Host ""
Write-Host "This window will close in 10 seconds..." -ForegroundColor Gray

# Wait before closing
Start-Sleep -Seconds 10