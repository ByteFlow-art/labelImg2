@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

title LabelImg2 Next-Gen

set "ENV_NAME=labelimg2"
set "APP_FILE=labelImg.py"

if not exist "%SCRIPT_DIR%%APP_FILE%" (
    echo [ERROR] Cannot find %APP_FILE% in %SCRIPT_DIR%
    pause
    exit /b 1
)

set "PYTHON_EXE="

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    goto :START_APP
)

if exist "%SCRIPT_DIR%python_embed\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%python_embed\python.exe"
    goto :START_APP
)

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
    call "!CONDA_ACTIVATE!" "%ENV_NAME%" >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where python 2^>nul') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
        )
        if defined PYTHON_EXE (
            if defined CONDA_PREFIX (
                set "QT_QPA_PLATFORM_PLUGIN_PATH=%CONDA_PREFIX%\Library\plugins\platforms"
            )
            goto :START_APP
        )
    )
)

for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
)

if defined PYTHON_EXE (
    "!PYTHON_EXE!" -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        goto :START_APP
    )
)

echo [*] Initializing LabelImg2 environment...
call "%SCRIPT_DIR%setup_env.bat"
exit /b 0

:START_APP
echo [*] Launching LabelImg2 Workstation...
start "" "!PYTHON_EXE!" "%SCRIPT_DIR%%APP_FILE%" %*
endlocal
exit /b 0
