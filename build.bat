@echo off
echo Building SoulSense Desktop Application...
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install PyInstaller if not present
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the application
echo.
echo Building executable...
pyinstaller soulsense.spec

echo.
if exist dist\SoulSense\SoulSense.exe (
    echo Build successful! Executable located at: dist\SoulSense\SoulSense.exe
) else (
    echo Build failed. Check the output above for errors.
)

pause
