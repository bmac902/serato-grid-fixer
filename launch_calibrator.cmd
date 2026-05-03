@echo off
cd /d "%~dp0"
title Serato Grid Fixer - Calibrator
python "%~dp0calibrate_buttons.py"
echo.
echo Calibration finished.
echo You can close this window.
pause
