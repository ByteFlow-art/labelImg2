@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"
title LabelImg2

set "APP_FILE=labelImg.py"
if not exist "%SCRIPT_DIR%\%APP_FILE%" (
    if exist "%SCRIPT_DIR%\main.py" set "APP_FILE=main.py"
)

if not exist "%SCRIPT_DIR%\%APP_FILE%" (
    echo [ERROR] Cannot find main application file: %APP_FILE%
    echo Directory: %SCRIPT_DIR%
    pause
    exit /b 1
)

set "TARGET_PYTHON="

REM 0. Check application dedicated runtime (python_runtime)
if exist "%SCRIPT_DIR%\python_runtime\pythonw.exe" (
    "%SCRIPT_DIR%\python_runtime\pythonw.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%\python_runtime\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%\python_runtime\python.exe" (
    "%SCRIPT_DIR%\python_runtime\python.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%\python_runtime\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

REM 1. Check local virtual environment (.venv)
if exist "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" (
    "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "import PyQt5" >nul 2>&1
    if !errorlevel! EQU 0 (
        start "" "%SCRIPT_DIR%\.venv\Scripts\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

REM 2. Check direct Conda labelimg2 environment
for %%P in (
    "C:\D\Conda\miniconda3\envs\labelimg2\pythonw.exe"
    "C:\D\Conda\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\miniconda3\envs\labelimg2\pythonw.exe"
    "%USERPROFILE%\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\anaconda3\envs\labelimg2\pythonw.exe"
    "%USERPROFILE%\anaconda3\envs\labelimg2\python.exe"
    "%LOCALAPPDATA%\miniconda3\envs\labelimg2\pythonw.exe"
    "%LOCALAPPDATA%\miniconda3\envs\labelimg2\python.exe"
    "%LOCALAPPDATA%\anaconda3\envs\labelimg2\pythonw.exe"
    "%LOCALAPPDATA%\anaconda3\envs\labelimg2\python.exe"
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
        if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~P"
    )
)

if defined TARGET_PYTHON (
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM 3. Check Windows Python Launcher (py.exe)
where py.exe >nul 2>&1
if !errorlevel! EQU 0 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined TARGET_PYTHON if exist "%%~I" (
            "%%~I" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~I"
        )
    )
)

if defined TARGET_PYTHON (
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM 4. Check standard Python installation directories
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python38\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python38\python.exe"
    "C:\Program Files\Python313\pythonw.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\pythonw.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\pythonw.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\pythonw.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Program Files\Python39\pythonw.exe"
    "C:\Program Files\Python39\python.exe"
    "C:\Program Files\Python38\pythonw.exe"
    "C:\Program Files\Python38\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "C:\Python38\python.exe"
    "D:\Python313\python.exe"
    "D:\Python312\python.exe"
    "D:\Python311\python.exe"
    "D:\Python310\python.exe"
    "D:\Python39\python.exe"
    "D:\Python38\python.exe"
) do (
    if not defined TARGET_PYTHON if exist "%%~P" (
        "%%~P" -c "import PyQt5" >nul 2>&1
        if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~P"
    )
)

if defined TARGET_PYTHON (
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM 5. Check Windows Registry
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
    if not defined TARGET_PYTHON if exist "%%~B" (
        "%%~B" -c "import PyQt5" >nul 2>&1
        if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~B"
    )
)
if not defined TARGET_PYTHON (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
        if not defined TARGET_PYTHON if exist "%%~B" (
            "%%~B" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~B"
        )
    )
)

if defined TARGET_PYTHON (
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM 6. Check Conda activate script
set "CONDA_ACTIVATE="
for %%P in (
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "%LOCALAPPDATA%\miniconda3\Scripts\activate.bat"
    "%LOCALAPPDATA%\anaconda3\Scripts\activate.bat"
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
                start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
                exit /b 0
            )
        )
        for /f "delims=" %%I in ('where python.exe 2^>nul') do (
            "%%~fI" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 (
                start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
                exit /b 0
            )
        )
    )
)

REM 7. Check system PATH
for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
    set "CANDIDATE=%%~fI"
    echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
    if errorlevel 1 (
        "%%~fI" -c "import PyQt5" >nul 2>&1
        if !errorlevel! EQU 0 (
            start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
            exit /b 0
        )
    )
)
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    set "CANDIDATE=%%~fI"
    echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
    if errorlevel 1 (
        "%%~fI" -c "import PyQt5" >nul 2>&1
        if !errorlevel! EQU 0 (
            start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
            exit /b 0
        )
    )
)

REM 8. Auto setup environment on first run if setup_env.bat exists
echo ==============================================================================
echo                 LabelImg2 - Auto Initializing Environment
echo ==============================================================================
echo Detecting and setting up LabelImg2 runtime environment, please wait...
echo.

if exist "%SCRIPT_DIR%\setup_env.bat" (
    call "%SCRIPT_DIR%\setup_env.bat" --auto
    if exist "%SCRIPT_DIR%\python_runtime\pythonw.exe" (
        start "" "%SCRIPT_DIR%\python_runtime\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
    if exist "%SCRIPT_DIR%\python_runtime\python.exe" (
        start "" "%SCRIPT_DIR%\python_runtime\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
    if exist "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" (
        start "" "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
    if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
        start "" "%SCRIPT_DIR%\.venv\Scripts\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        set "CANDIDATE=%%~fI"
        echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
        if errorlevel 1 (
            "%%~fI" -c "import PyQt5" >nul 2>&1
            if !errorlevel! EQU 0 (
                start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
                exit /b 0
            )
        )
    )
)

echo.
echo [ERROR] No compatible Python 3.8+ environment found on your system.
echo Please install Python (https://www.python.org/downloads/) and check "Add Python to PATH".
pause
exit /b 0
