@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 - Smart High-Speed Launcher
REM   Priority:
REM   1. Dedicated Conda environment ('labelimg2')
REM   2. Local isolated virtual environment ('.venv')
REM   3. Application portable runtime ('python_runtime')
REM   4. System Conda / Python 3.8+ with verified PyQt5, lxml, Pillow
REM   5. Automatic self-healing via 'setup_env.bat' (Never silent crash!)
REM ==============================================================================

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

REM ------------------------------------------------------------------------------
REM 0. High-Speed Cache: Instant launch using cached Python interpreter (.python_path)
REM ------------------------------------------------------------------------------
set "CACHE_FILE=%SCRIPT_DIR%\.python_path"
if exist "%CACHE_FILE%" (
    set "CACHED_PYTHON="
    set /p CACHED_PYTHON=<"%CACHE_FILE%"
    if defined CACHED_PYTHON if exist "!CACHED_PYTHON!" (
        start "" "!CACHED_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

set "TARGET_PYTHON="

REM ------------------------------------------------------------------------------
REM 1. Check dedicated Conda 'labelimg2' environment (Highest priority for AI/CV users)
REM ------------------------------------------------------------------------------
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
        "%%~P" -c "import PyQt5, lxml, PIL" >nul 2>&1
        if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~P"
    )
)

if defined TARGET_PYTHON (
    echo !TARGET_PYTHON!> "%CACHE_FILE%" 2>nul
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM ------------------------------------------------------------------------------
REM 2. Dedicated portable runtime (python_runtime) if bundled with the app (Zero-dependency PCs)
REM ------------------------------------------------------------------------------
if exist "%SCRIPT_DIR%\python_runtime\pythonw.exe" (
    "%SCRIPT_DIR%\python_runtime\pythonw.exe" -c "import PyQt5, lxml, PIL" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo %SCRIPT_DIR%\python_runtime\pythonw.exe> "%CACHE_FILE%" 2>nul
        start "" "%SCRIPT_DIR%\python_runtime\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%\python_runtime\python.exe" (
    "%SCRIPT_DIR%\python_runtime\python.exe" -c "import PyQt5, lxml, PIL" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo %SCRIPT_DIR%\python_runtime\python.exe> "%CACHE_FILE%" 2>nul
        start "" "%SCRIPT_DIR%\python_runtime\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

REM ------------------------------------------------------------------------------
REM 3. Check local virtual environment (.venv)
REM ------------------------------------------------------------------------------
if exist "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" (
    "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" -c "import PyQt5, lxml, PIL" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo %SCRIPT_DIR%\.venv\Scripts\pythonw.exe> "%CACHE_FILE%" 2>nul
        start "" "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "import PyQt5, lxml, PIL" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo %SCRIPT_DIR%\.venv\Scripts\python.exe> "%CACHE_FILE%" 2>nul
        start "" "%SCRIPT_DIR%\.venv\Scripts\python.exe" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

REM ------------------------------------------------------------------------------
REM 4. Check system standard Python installations (Python 3.8 - 3.13)
REM ------------------------------------------------------------------------------
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python38\pythonw.exe"
    "C:\Program Files\Python313\pythonw.exe"
    "C:\Program Files\Python312\pythonw.exe"
    "C:\Program Files\Python311\pythonw.exe"
    "C:\Program Files\Python310\pythonw.exe"
    "C:\Program Files\Python39\pythonw.exe"
    "C:\Program Files\Python38\pythonw.exe"
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
        "%%~P" -c "import PyQt5, lxml, PIL" >nul 2>&1
        if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~P"
    )
)

if defined TARGET_PYTHON (
    echo !TARGET_PYTHON!> "%CACHE_FILE%" 2>nul
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM ------------------------------------------------------------------------------
REM 5. Check Windows Python Launcher (py.exe) and Registry
REM ------------------------------------------------------------------------------
where py.exe >nul 2>&1
if !errorlevel! EQU 0 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined TARGET_PYTHON if exist "%%~I" (
            "%%~I" -c "import PyQt5, lxml, PIL" >nul 2>&1
            if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~I"
        )
    )
)

if not defined TARGET_PYTHON (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
        if not defined TARGET_PYTHON if exist "%%~B" (
            "%%~B" -c "import PyQt5, lxml, PIL" >nul 2>&1
            if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~B"
        )
    )
)

if defined TARGET_PYTHON (
    echo !TARGET_PYTHON!> "%CACHE_FILE%" 2>nul
    start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
    exit /b 0
)

REM ------------------------------------------------------------------------------
REM 6. Check system PATH
REM ------------------------------------------------------------------------------
for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
    set "CANDIDATE=%%~fI"
    echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
    if errorlevel 1 (
        "%%~fI" -c "import PyQt5, lxml, PIL" >nul 2>&1
        if !errorlevel! EQU 0 (
            echo %%~fI> "%CACHE_FILE%" 2>nul
            start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
            exit /b 0
        )
    )
)
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    set "CANDIDATE=%%~fI"
    echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
    if errorlevel 1 (
        "%%~fI" -c "import PyQt5, lxml, PIL" >nul 2>&1
        if !errorlevel! EQU 0 (
            echo %%~fI> "%CACHE_FILE%" 2>nul
            start "" "%%~fI" "%SCRIPT_DIR%\%APP_FILE%"
            exit /b 0
        )
    )
)

REM ------------------------------------------------------------------------------
REM 7. Auto setup environment on first run if setup_env.bat exists (Self-healing)
REM ------------------------------------------------------------------------------
echo ==============================================================================
echo                 LabelImg2 - Auto Initializing Environment
echo ==============================================================================
echo Detecting and setting up LabelImg2 runtime environment, please wait...
echo.

if exist "%SCRIPT_DIR%\setup_env.bat" (
    call "%SCRIPT_DIR%\setup_env.bat" --auto

    REM Re-check prioritized environments after setup
    for %%P in (
        "C:\D\Conda\miniconda3\envs\labelimg2\pythonw.exe"
        "C:\D\Conda\miniconda3\envs\labelimg2\python.exe"
        "%USERPROFILE%\miniconda3\envs\labelimg2\pythonw.exe"
        "%USERPROFILE%\miniconda3\envs\labelimg2\python.exe"
        "%LOCALAPPDATA%\miniconda3\envs\labelimg2\pythonw.exe"
        "%LOCALAPPDATA%\miniconda3\envs\labelimg2\python.exe"
        "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe"
        "%SCRIPT_DIR%\.venv\Scripts\python.exe"
        "%SCRIPT_DIR%\python_runtime\pythonw.exe"
        "%SCRIPT_DIR%\python_runtime\python.exe"
    ) do (
        if not defined TARGET_PYTHON if exist "%%~P" (
            "%%~P" -c "import PyQt5, lxml, PIL" >nul 2>&1
            if !errorlevel! EQU 0 set "TARGET_PYTHON=%%~P"
        )
    )

    if defined TARGET_PYTHON (
        start "" "!TARGET_PYTHON!" "%SCRIPT_DIR%\%APP_FILE%"
        exit /b 0
    )
)

echo.
echo ==============================================================================
echo [ERROR] No ready-to-use Python environment found on your system.
echo ==============================================================================
echo Please run 'setup_env.bat' directly to view the full environment setup log,
echo or install Python 3.8+ (https://www.python.org/downloads/) / Miniconda.
echo.
pause
exit /b 1
