@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
title LabelImg2 Uninstaller

REM 1. Try local venv Python
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    start "" "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%uninstall_gui.py" "%SCRIPT_DIR%"
    exit /b 0
)

REM 2. Try python_embed
if exist "%SCRIPT_DIR%python_embed\python.exe" (
    start "" "%SCRIPT_DIR%python_embed\python.exe" "%SCRIPT_DIR%uninstall_gui.py" "%SCRIPT_DIR%"
    exit /b 0
)

REM 3. Try conda env
set "CONDA_ACTIVATE="
for %%P in (
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\ProgramData\anaconda3\Scripts\activate.bat"
    "C:\Miniconda3\Scripts\activate.bat"
    "C:\Anaconda3\Scripts\activate.bat"
    "D:\Anaconda3\Scripts\activate.bat"
    "D:\miniconda3\Scripts\activate.bat"
) do (
    if not defined CONDA_ACTIVATE if exist "%%~P" set "CONDA_ACTIVATE=%%~P"
)

if defined CONDA_ACTIVATE (
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
    if not errorlevel 1 (
        if defined CONDA_PREFIX (
            start "" "!CONDA_PREFIX!\python.exe" "%SCRIPT_DIR%uninstall_gui.py" "%SCRIPT_DIR%"
            exit /b 0
        )
    )
)

REM 4. Try system Python
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    start "" "%%~fI" "%SCRIPT_DIR%uninstall_gui.py" "%SCRIPT_DIR%"
    exit /b 0
)

REM 5. Fallback CLI
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%uninstall_gui.py" "%SCRIPT_DIR%"
exit /b 0
