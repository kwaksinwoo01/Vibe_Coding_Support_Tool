@echo off
setlocal
cd /d "%~dp0"

echo Building vibeStation with the repository Python version...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Invoke-VibeStationBuild.ps1" %*
set "BUILD_EXIT=%ERRORLEVEL%"

if not "%BUILD_EXIT%"=="0" (
    echo.
    echo Build failed with exit code %BUILD_EXIT%.
    exit /b %BUILD_EXIT%
)

echo.
echo Build successful.
echo Executable location: dist\vibeStation.exe
exit /b 0
