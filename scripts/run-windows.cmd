@echo off
setlocal
cd /d "%~dp0\.."
py -3 app\plotter.py
if errorlevel 1 (
    echo.
    echo One Click Mesh could not start. Check Python, dependencies, and internet access.
    pause
)
