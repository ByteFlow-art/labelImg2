@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
title LabelImg2

set "APP_FILE=labelImg.py"

if not exist "%SCRIPT_DIR%%APP_FILE%" (
    echo [ERROR] Cannot find main application file: %APP_FILE%
    echo Script Directory: %SCRIPT_DIR%
    pause
    exit /b 1
)

REM 1. Check direct Conda labelimg2 environment
set "TARGET_PYTHON="
for %%P in (
    "C:\D\Conda\miniconda3\envs\labelimg2\pythonw.exe"
    "C:\D\Conda\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\miniconda3\envs\labelimg2\pythonw.exe"
    "%USERPROFILE%\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\anaconda3\envs\labelimg2\pythonw.exe"
    "%USERPROFILE%\anaconda3\envs\labelimg2\python.exe"
    "C:\ProgramData\miniconda3\envs\labelimg2\pythonw.exe"
    "C:\ProgramData\miniconda3\envs\labelimg2\python.exe"
    "C:\ProgramData\anaconda3\envs\labelimg2\pythonw.exe"
    "C:\ProgramData\anaconda3\envs\labelimg2\python.exe"
    "C:\Miniconda3\envs\labelimg2\pythonw.exe"
    "C:\Miniconda3\envs\labelimg2\python.exe"
    "C:\Anaconda3\envs\labelimg2\pythonw.exe"
    "C:\Anaconda3\envs\labelimg2\python.exe"
    "D:\Anaconda3\envs\labelimg2\pythonw.exe"
    "D:\Anaconda3\envs\labelimg2\python.exe"
    "D:\miniconda3\envs\labelimg2\pythonw.exe"
    "D:\miniconda3\envs\labelimg2\python.exe"
) do (
    if not defined TARGET_PYTHON if exist "%%~P" (
        "%%~P" -c "import PyQt5" >nul 2>&1
        if !errorlevel! EQU 0 (
            set "TARGET_PYTHON=%%~P"
        )
    )
)

if defined TARGET_PYTHON (
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%%APP_FILE%"
    exit /b 0
)

REM 2. Check local virtual environment (.venv)
if exist "%SCRIPT_DIR%.venv\Scripts\pythonw.exe" (
    "%SCRIPT_DIR%.venv\Scripts\pythonw.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%.venv\Scripts\pythonw.exe" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)

REM 3. Check local embedded Python (python_embed)
if exist "%SCRIPT_DIR%python_embed\pythonw.exe" (
    "%SCRIPT_DIR%python_embed\pythonw.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%python_embed\pythonw.exe" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%python_embed\python.exe" (
    "%SCRIPT_DIR%python_embed\python.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%python_embed\python.exe" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)

REM 4. Check Conda activate scripts
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

if not defined CONDA_ACTIVATE (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
        if not defined CONDA_ACTIVATE set "CONDA_ACTIVATE=%%~fI"
    )
)

if defined CONDA_ACTIVATE (
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
    if !errorlevel! EQU 0 (
        for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
            "%%~fI" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 (
                start "" "%%~fI" "%SCRIPT_DIR%%APP_FILE%"
                exit /b 0
            )
        )
        for /f "delims=" %%I in ('where python.exe 2^>nul') do (
            "%%~fI" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 (
                start "" "%%~fI" "%SCRIPT_DIR%%APP_FILE%"
                exit /b 0
            )
        )
    )
)

REM 5. Check system Python with PyQt5
for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
    "%%~fI" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%%~fI" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    "%%~fI" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%%~fI" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
)

REM 5. Auto setup environment on first run if setup_env.bat exists
echo ==============================================================================
echo                 LabelImg2 - Auto Initializing Environment
echo ==============================================================================
echo.
if exist "%SCRIPT_DIR%setup_env.bat" (
    call "%SCRIPT_DIR%setup_env.bat" --auto
    if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
        start "" "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%%APP_FILE%"
        exit /b 0
    )
) else (
    echo [ERROR] No compatible Python environment with PyQt5 found.
    pause
)

exit /b 1

