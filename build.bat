@echo off
REM Build script for vibeStation Windows EXE

echo Building vibeStation...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Build the executable
echo Running PyInstaller...
pyinstaller vibestation.spec

if errorlevel 0 (
    echo.
    echo Build successful!
    echo Executable location: dist\vibeStation.exe
    echo.
    pause
) else (
    echo.
    echo Build failed!
    echo.
    pause
)
