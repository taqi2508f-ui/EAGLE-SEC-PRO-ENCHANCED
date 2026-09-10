@echo off
title EAGLE-SEC PRO
color 0B
echo.
echo  ========================================================
echo   EAGLE-SEC PRO v1.0.0 - Starting...
echo  ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.12+
    pause
    exit /b 1
)

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Application crashed. Check logs\eagle_sec.log for details.
    pause
)
