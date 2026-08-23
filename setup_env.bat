@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 - Automated Environment Setup Wizard
REM ==============================================================================

title LabelImg2 Environment Setup

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "IS_AUTO_MODE=0"
if /i "%~1"=="--auto" set "IS_AUTO_MODE=1"
if /i "%~1"=="-y" set "IS_AUTO_MODE=1"

set "PYTHON_EXE="
set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
set "TRUSTED_HOST=--trusted-host pypi.tuna.tsinghua.edu.cn"

echo.
echo ==============================================================================
echo            LabelImg2 Next-Gen - Automated Environment Setup
echo ==============================================================================
echo.

echo [Step 1/5] Detecting Python / Conda runtime environment...

REM 1. Check local virtual environment (.venv)
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    echo [OK] Found local virtual environment: .venv\Scripts\python.exe
    goto :INSTALL_DEPS
)

REM 2. Check direct Conda environment python.exe path
for %%D in (
    "C:\D\Conda\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\miniconda3\envs\labelimg2\python.exe"
    "%USERPROFILE%\anaconda3\envs\labelimg2\python.exe"
    "C:\ProgramData\miniconda3\envs\labelimg2\python.exe"
    "C:\ProgramData\anaconda3\envs\labelimg2\python.exe"
    "C:\Miniconda3\envs\labelimg2\python.exe"
    "C:\Anaconda3\envs\labelimg2\python.exe"
    "D:\miniconda3\envs\labelimg2\python.exe"
    "D:\Anaconda3\envs\labelimg2\python.exe"
) do (
    if not defined PYTHON_EXE if exist "%%~D" (
        set "PYTHON_EXE=%%~D"
        echo [OK] Found Conda environment python: %%~D
        goto :INSTALL_DEPS
    )
)

REM 3. Check Conda activate scripts
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
        if not defined CONDA_ACTIVATE (
            set "CONDA_DIR=%%~dpI"
            if exist "!CONDA_DIR!activate.bat" set "CONDA_ACTIVATE=!CONDA_DIR!activate.bat"
        )
    )
)

if defined CONDA_ACTIVATE (
    echo [OK] Found Conda package manager: !CONDA_ACTIVATE!
    echo [Step 2/5] Initializing Conda environment [labelimg2]...
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
    if defined CONDA_PREFIX (
        set "PYTHON_EXE=!CONDA_PREFIX!\python.exe"
        echo [OK] Activated existing Conda environment [labelimg2]
        goto :INSTALL_DEPS
    )
    echo [*] Creating new Conda environment [labelimg2] (Python 3.10)...
    call "!CONDA_ACTIVATE!" base
    call conda create -n labelimg2 python=3.10 -y
    call "!CONDA_ACTIVATE!" labelimg2
    if defined CONDA_PREFIX (
        set "PYTHON_EXE=!CONDA_PREFIX!\python.exe"
        echo [OK] Created and activated Conda environment [labelimg2]
        goto :INSTALL_DEPS
    )
)

REM 4. Check system Python
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE (
        set "CANDIDATE=%%~fI"
        echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
        if errorlevel 1 (
            set "PYTHON_EXE=!CANDIDATE!"
        )
    )
)

if defined PYTHON_EXE (
    echo [OK] Found system Python: !PYTHON_EXE!
    echo [Step 2/5] Creating project virtual environment (.venv)...
    "!PYTHON_EXE!" -m venv "%SCRIPT_DIR%.venv"
    if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
        echo [OK] Local virtual environment created: .venv
        goto :INSTALL_DEPS
    )
)

REM 5. Fallback: prompt to install Python
echo.
echo [WARNING] No Python 3.8+ or Conda environment detected on your system.
echo Please install Python (https://www.python.org/downloads/) and add it to PATH.
echo.
if "%IS_AUTO_MODE%"=="0" pause
exit /b 1

:INSTALL_DEPS
echo.
echo [Step 3/5] Upgrading pip with high-speed mirror...
"!PYTHON_EXE!" -m pip install --upgrade pip -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1

echo.
echo [Step 4/5] Installing core dependencies (PyQt5, Ultralytics, PyTorch, OpenCV, lxml)...
"!PYTHON_EXE!" -m pip install -r requirements.txt -i !PIP_INDEX! !TRUSTED_HOST!

if errorlevel 1 (
    echo.
    echo [Retry] Retrying with Aliyun mirror...
    "!PYTHON_EXE!" -m pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
)

echo.
echo [Step 5/5] Verifying LabelImg2 runtime dependencies...
"!PYTHON_EXE!" -c "import PyQt5, torch, ultralytics, cv2, PIL, lxml, yaml; print('[OK] All dependencies successfully verified!')"

if errorlevel 1 (
    echo.
    echo [WARNING] Some dependencies failed to load. Please check error output above.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

REM Create Desktop Shortcut
set "TARGET_BAT=%SCRIPT_DIR%Start_LabelImg2.bat"
if exist "%SCRIPT_DIR%img\app.ico" (
    set "ICON_FILE=%SCRIPT_DIR%img\app.ico"
) else (
    set "ICON_FILE=%SCRIPT_DIR%img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut($d + '\LabelImg2.lnk'); $s.TargetPath = $env:TARGET_BAT; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = $env:ICON_FILE + ',0'; $s.Description = 'LabelImg2 Next-Gen'; $s.Save();" >nul 2>&1

echo.
echo ==============================================================================
echo   [SUCCESS] LabelImg2 environment deployment complete!
echo   A desktop shortcut [LabelImg2] has been created on your Desktop.
echo   You can now launch LabelImg2 via desktop shortcut or Start_LabelImg2.bat.
echo ==============================================================================
echo.

if "%IS_AUTO_MODE%"=="1" exit /b 0

set "LAUNCH_NOW=Y"
set /p LAUNCH_NOW="Launch LabelImg2 now? (Y/N, default Y): "
if /i "%LAUNCH_NOW%"=="" set "LAUNCH_NOW=Y"
if /i "%LAUNCH_NOW%"=="Y" (
    start "" "%SCRIPT_DIR%Start_LabelImg2.bat"
)

endlocal
exit /b 0
