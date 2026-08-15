@echo off
cd /d "%~dp0"
title Serato Grid Fixer

rem Prefer the Windows Python launcher: it finds the real Python install even when
rem another tool has put its own venv ahead of it on PATH.
set "PY=py"
where py >nul 2>&1 || set "PY=python"

%PY% -c "import keyboard, pyautogui, pynput" 2>nul
if errorlevel 1 (
    echo Missing dependencies - installing from requirements.txt...
    %PY% -m pip install -r "%~dp0requirements.txt"
    echo.
)

%PY% "%~dp0grid_fixer.py"
echo.
echo Serato Grid Fixer has exited.
echo You can close this window.
pause
