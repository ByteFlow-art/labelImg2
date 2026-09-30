@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 - Automated Environment Setup Wizard
REM ==============================================================================

title LabelImg2 Environment Setup

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
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
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    echo [OK] Found local virtual environment: .venv\Scripts\python.exe
)

REM 2. Check dedicated Conda environment paths
if not defined PYTHON_EXE (
    for %%D in (
        "C:\D\Conda\miniconda3\envs\labelimg2\python.exe"
        "%USERPROFILE%\miniconda3\envs\labelimg2\python.exe"
        "%USERPROFILE%\anaconda3\envs\labelimg2\python.exe"
        "%LOCALAPPDATA%\miniconda3\envs\labelimg2\python.exe"
        "%LOCALAPPDATA%\anaconda3\envs\labelimg2\python.exe"
        "C:\ProgramData\miniconda3\envs\labelimg2\python.exe"
        "C:\ProgramData\anaconda3\envs\labelimg2\python.exe"
        "C:\Miniconda3\envs\labelimg2\python.exe"
        "C:\Anaconda3\envs\labelimg2\python.exe"
        "D:\miniconda3\envs\labelimg2\python.exe"
        "D:\Anaconda3\envs\labelimg2\python.exe"
    ) do (
        if not defined PYTHON_EXE if exist "%%~D" (
            set "PYTHON_EXE=%%~D"
            echo [OK] Found Conda environment: %%~D
        )
    )
)

REM 3. Check Windows Python Launcher (py.exe)
if not defined PYTHON_EXE (
    where py.exe >nul 2>&1
    if !errorlevel! EQU 0 (
        for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
            if not defined PYTHON_EXE if exist "%%~I" (
                set "PYTHON_EXE=%%~I"
                echo [OK] Found system Python via py.exe launcher: %%~I
            )
        )
    )
)

REM 4. Check standard Python installation directories (Python 3.8 - 3.13)
if not defined PYTHON_EXE (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python38\python.exe"
        "C:\Program Files\Python313\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python310\python.exe"
        "C:\Program Files\Python39\python.exe"
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
        if not defined PYTHON_EXE if exist "%%~D" (
            set "PYTHON_EXE=%%~D"
            echo [OK] Found standard path Python: %%~D
        )
    )
)

REM 5. Check Windows Registry
if not defined PYTHON_EXE (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
        if not defined PYTHON_EXE if exist "%%~B" (
            set "PYTHON_EXE=%%~B"
            echo [OK] Found Python in user registry: %%~B
        )
    )
)
if not defined PYTHON_EXE (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
        if not defined PYTHON_EXE if exist "%%~B" (
            set "PYTHON_EXE=%%~B"
            echo [OK] Found Python in system registry: %%~B
        )
    )
)

REM 6. Check Conda activate script
if not defined PYTHON_EXE (
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
            if not defined CONDA_ACTIVATE (
                set "CONDA_DIR=%%~dpI"
                if exist "!CONDA_DIR!activate.bat" set "CONDA_ACTIVATE=!CONDA_DIR!activate.bat"
            )
        )
    )
    if defined CONDA_ACTIVATE (
        echo [OK] Found Conda package manager: !CONDA_ACTIVATE!
        call "!CONDA_ACTIVATE!" base >nul 2>&1
        for /f "delims=" %%I in ('where python.exe 2^>nul') do (
            if not defined PYTHON_EXE if exist "%%~fI" set "PYTHON_EXE=%%~fI"
        )
    )
)

REM 7. Check system PATH
if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        if not defined PYTHON_EXE (
            set "CANDIDATE=%%~fI"
            echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
            if errorlevel 1 (
                set "PYTHON_EXE=!CANDIDATE!"
                echo [OK] Found system PATH Python: !PYTHON_EXE!
            )
        )
    )
)

if not defined PYTHON_EXE (
    echo.
    echo [WARNING] No Python 3.8+ or Conda runtime environment detected.
    echo Please download and install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

echo [OK] Selected Python interpreter: !PYTHON_EXE!

echo [Step 2/5] Initializing local virtual environment...
if not exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    "!PYTHON_EXE!" -m venv "%SCRIPT_DIR%\.venv" >nul 2>&1
)

if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "RUN_PYTHON=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    echo [OK] Local virtual environment ready: .venv
) else (
    set "RUN_PYTHON=!PYTHON_EXE!"
    echo [NOTE] Using main Python environment directly.
)

echo.
echo [Step 3/5] Upgrading pip...
"!RUN_PYTHON!" -m pip install --upgrade pip -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1

echo.
echo [Step 4/5] Installing core dependencies (PyQt5, lxml, Pillow, pyyaml)...
"!RUN_PYTHON!" -m pip install "pyqt5>=5.15.0" "lxml>=4.9.0" "Pillow>=9.5.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" -i !PIP_INDEX! !TRUSTED_HOST!
if errorlevel 1 (
    echo [Retry] Retrying with Aliyun mirror...
    "!RUN_PYTHON!" -m pip install "pyqt5>=5.15.0" "lxml>=4.9.0" "Pillow>=9.5.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
)

echo.
echo [*] Installing optional packages (OpenCV / AI center)...
"!RUN_PYTHON!" -m pip install "opencv-python>=4.7.0" "numpy>=1.23.0" -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1

echo.
echo [Step 5/5] Verifying LabelImg2 core runtime...
"!RUN_PYTHON!" -c "import PyQt5, lxml, PIL, yaml; print('[OK] Core dependencies verified successfully!')"
if errorlevel 1 (
    echo [WARNING] Core dependencies verification encountered issues.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

REM Create Desktop Shortcut
set "TARGET_BAT=%SCRIPT_DIR%\Start_LabelImg2.bat"
if exist "%SCRIPT_DIR%\img\app.ico" (
    set "ICON_FILE=%SCRIPT_DIR%\img\app.ico"
) else (
    set "ICON_FILE=%SCRIPT_DIR%\img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $dirs = @([Environment]::GetFolderPath('Desktop'), \"$env:USERPROFILE\Desktop\", \"$env:USERPROFILE\OneDrive\Desktop\"); foreach ($d in $dirs) { if ($d -and (Test-Path $d)) { try { $s = $ws.CreateShortcut((Join-Path $d 'LabelImg2.lnk')); $s.TargetPath = $env:TARGET_BAT; $s.WorkingDirectory = $env:SCRIPT_DIR; $s.IconLocation = $env:ICON_FILE + ',0'; $s.Description = 'LabelImg2'; $s.Save(); } catch {} } }; $sm = [Environment]::GetFolderPath('Programs'); if ($sm -and (Test-Path $sm)) { try { $s2 = $ws.CreateShortcut((Join-Path $sm 'LabelImg2.lnk')); $s2.TargetPath = $env:TARGET_BAT; $s2.WorkingDirectory = $env:SCRIPT_DIR; $s2.IconLocation = $env:ICON_FILE + ',0'; $s2.Description = 'LabelImg2'; $s2.Save(); } catch {} }" >nul 2>&1

echo.
echo ==============================================================================
echo   [SUCCESS] LabelImg2 runtime environment setup complete!
echo   A desktop shortcut [LabelImg2] has been created on your Desktop.
echo ==============================================================================
echo.

if "%IS_AUTO_MODE%"=="1" exit /b 0

set "LAUNCH_NOW=Y"
set /p LAUNCH_NOW="Launch LabelImg2 now? (Y/N, default Y): "
if /i "%LAUNCH_NOW%"=="" set "LAUNCH_NOW=Y"
if /i "%LAUNCH_NOW%"=="Y" (
    start "" "%SCRIPT_DIR%\Start_LabelImg2.bat"
)

endlocal
exit /b 0
