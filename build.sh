#!/bin/bash
# Build script for vibeStation

echo "Building vibeStation..."
echo

# Check if PyInstaller is installed
python3 -c "import PyInstaller" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Build the executable
echo "Running PyInstaller..."
pyinstaller vibestation.spec

if [ $? -eq 0 ]; then
    echo
    echo "Build successful!"
    echo "Executable location: dist/vibeStation"
    echo
else
    echo
    echo "Build failed!"
    echo
fi
