# Soul Sense Application Launcher
# This script activates the virtual environment and runs the application

# Activate virtual environment
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# Run the application
python -m app.main
