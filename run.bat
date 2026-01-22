@echo off
REM Soul Sense Application Launcher for Windows
REM Activates virtual environment and runs the application

call .venv\Scripts\activate.bat
python -m app.main
