@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ==============================================================================
REM   LabelImg2 - Automated Environment Setup Wizard
REM   Supports:
REM   1. Automatic Conda Detection and Dedicated 'labelimg2' Environment Creation
REM   2. Zero-Environment Automated Fallback (Standalone Portable Python 3.10)
REM   3. Strict Error Reporting and Full Verification Feedback to Terminal
REM ==============================================================================

title LabelImg2 Environment Setup

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"

set "IS_AUTO_MODE=0"
if /i "%~1"=="--auto" set "IS_AUTO_MODE=1"
if /i "%~1"=="-y" set "IS_AUTO_MODE=1"

set "PYTHON_EXE="
set "RUN_PYTHON="
set "IS_CONDA_ENV=0"
set "IS_PORTABLE_ENV=0"
set "PIP_INDEX=https://mirrors.cloud.tencent.com/pypi/simple"
set "TRUSTED_HOST=--trusted-host mirrors.cloud.tencent.com"

echo.
echo ==============================================================================
echo            LabelImg2 Next-Gen - Automated Environment Setup
echo ==============================================================================
echo.

echo [Step 1/5] Detecting and preparing Python / Conda runtime environment...

REM ------------------------------------------------------------------------------
REM Sub-step 1A: Search for Conda and manage dedicated 'labelimg2' environment
REM ------------------------------------------------------------------------------
set "CONDA_CMD="

if defined CONDA_EXE if exist "%CONDA_EXE%" set "CONDA_CMD=%CONDA_EXE%"

if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda.exe 2^>nul') do (
        if not defined CONDA_CMD set "CONDA_CMD=%%~fI"
    )
)
if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
        if not defined CONDA_CMD set "CONDA_CMD=%%~fI"
    )
)

if not defined CONDA_CMD (
    for %%C in (
        "C:\D\Conda\miniconda3\Scripts\conda.exe"
        "C:\D\Conda\miniconda3\condabin\conda.bat"
        "C:\D\Conda\miniconda3\_conda.exe"
        "%USERPROFILE%\miniconda3\Scripts\conda.exe"
        "%USERPROFILE%\miniconda3\condabin\conda.bat"
        "%USERPROFILE%\anaconda3\Scripts\conda.exe"
        "%USERPROFILE%\anaconda3\condabin\conda.bat"
        "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe"
        "%LOCALAPPDATA%\miniconda3\condabin\conda.bat"
        "%LOCALAPPDATA%\anaconda3\Scripts\conda.exe"
        "%LOCALAPPDATA%\anaconda3\condabin\conda.bat"
        "C:\ProgramData\miniconda3\Scripts\conda.exe"
        "C:\ProgramData\miniconda3\condabin\conda.bat"
        "C:\ProgramData\anaconda3\Scripts\conda.exe"
        "C:\ProgramData\anaconda3\condabin\conda.bat"
        "C:\Miniconda3\Scripts\conda.exe"
        "C:\Miniconda3\condabin\conda.bat"
        "C:\Anaconda3\Scripts\conda.exe"
        "C:\Anaconda3\condabin\conda.bat"
        "D:\miniconda3\Scripts\conda.exe"
        "D:\miniconda3\condabin\conda.bat"
        "D:\Anaconda3\Scripts\conda.exe"
        "D:\Anaconda3\condabin\conda.bat"
    ) do (
        if not defined CONDA_CMD if exist "%%~C" set "CONDA_CMD=%%~C"
    )
)

if defined CONDA_CMD (
    echo [OK] Detected Conda package manager: !CONDA_CMD!
    echo [*] Checking for dedicated 'labelimg2' Conda environment...

    set "CONDA_ENV_PY="
    for %%P in (
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
        if not defined CONDA_ENV_PY if exist "%%~P" set "CONDA_ENV_PY=%%~P"
    )

    if not defined CONDA_ENV_PY (
        echo [*] Conda environment 'labelimg2' not found.
        echo [*] Automatically creating dedicated isolated Conda environment 'labelimg2' (Python 3.10)...
        echo [*] Please wait while Conda provisions the environment...
        call "!CONDA_CMD!" create -y -n labelimg2 python=3.10
        if !errorlevel! NEQ 0 (
            echo [WARNING] 'conda create python=3.10' reported non-zero code. Retrying without python version lock...
            call "!CONDA_CMD!" create -y -n labelimg2 python
        )

        for %%P in (
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
            if not defined CONDA_ENV_PY if exist "%%~P" set "CONDA_ENV_PY=%%~P"
        )
    )

    if defined CONDA_ENV_PY (
        set "PYTHON_EXE=!CONDA_ENV_PY!"
        set "IS_CONDA_ENV=1"
        echo [OK] Successfully selected dedicated Conda environment: !PYTHON_EXE!
    )
)

REM ------------------------------------------------------------------------------
REM Sub-step 1B: If Conda is not used, check existing local or system Python
REM ------------------------------------------------------------------------------
if not defined PYTHON_EXE (
    REM Check application dedicated runtime (python_runtime)
    if exist "%SCRIPT_DIR%\python_runtime\python.exe" (
        set "PYTHON_EXE=%SCRIPT_DIR%\python_runtime\python.exe"
        set "IS_PORTABLE_ENV=1"
        echo [OK] Found dedicated portable Python runtime: python_runtime\python.exe
    )
)

if not defined PYTHON_EXE (
    REM Check local virtual environment (.venv)
    if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
        echo [OK] Found local virtual environment: .venv\Scripts\python.exe
    )
)

if not defined PYTHON_EXE (
    REM Check Windows Python Launcher (py.exe)
    where py.exe >nul 2>&1
    if !errorlevel! EQU 0 (
        for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
            if not defined PYTHON_EXE if exist "%%~I" (
                set "PYTHON_EXE=%%~I"
                echo [OK] Found system Python via py.exe: %%~I
            )
        )
    )
)

if not defined PYTHON_EXE (
    REM Check standard Python installation directories
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

if not defined PYTHON_EXE (
    REM Check Windows Registry
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

if not defined PYTHON_EXE (
    REM Check system PATH
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

REM ------------------------------------------------------------------------------
REM Sub-step 1C: Zero-Environment Automated Fallback (Micro-Kernel Embed Python 9.9 MB)
REM ------------------------------------------------------------------------------
if not defined PYTHON_EXE (
    echo.
    echo [Step 1/5] No Python/Conda detected on this computer.
    echo [*] Initiating ultra-lightweight micro-kernel deployment (only ~9.9 MB)...
    echo [*] Target destination: "%SCRIPT_DIR%\python_runtime"
    echo [*] Downloading official portable micro-kernel from high-speed mirror...

    set "EMBED_ZIP_TMP=%TEMP%\python_embed_%RANDOM%.zip"
    set "PY_TARGET_DIR=%SCRIPT_DIR%\python_runtime"

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]3072; } catch {}" ^
        "$urls = @(" ^
        "    'https://registry.npmmirror.com/-/binary/python/3.10.11/python-3.10.11-embed-amd64.zip'," ^
        "    'https://mirrors.huaweicloud.com/python/3.10.11/python-3.10.11-embed-amd64.zip'," ^
        "    'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip'" ^
        ");" ^
        "$out = $env:EMBED_ZIP_TMP;" ^
        "$downloaded = $false;" ^
        "foreach ($u in $urls) {" ^
        "    try {" ^
        "        Write-Host ('[*] Connecting to: ' + $u);" ^
        "        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {" ^
        "            & curl.exe -L -k --ssl-no-revoke --connect-timeout 15 $u -o $out;" ^
        "        } else {" ^
        "            $wc = New-Object System.Net.WebClient;" ^
        "            $wc.Headers.Add('User-Agent', 'Mozilla/5.0');" ^
        "            $wc.DownloadFile($u, $out);" ^
        "        }" ^
        "        if ((Test-Path $out) -and ((Get-Item $out).Length -gt 5000000)) {" ^
        "            $downloaded = $true;" ^
        "            Write-Host '[OK] Micro-kernel download completed successfully.';" ^
        "            break;" ^
        "        }" ^
        "    } catch {" ^
        "        Write-Host ('[!] Download warning on ' + $u + ': ' + $_.Exception.Message);" ^
        "    }" ^
        "}" ^
        "if (-not $downloaded) { Write-Host '[ERROR] All download mirrors failed or network unavailable.'; exit 1; }"

    if exist "!EMBED_ZIP_TMP!" (
        echo [*] Extracting portable micro-kernel into private directory...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$target = $env:PY_TARGET_DIR;" ^
            "if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target -Force | Out-Null };" ^
            "Expand-Archive -Path $env:EMBED_ZIP_TMP -DestinationPath $target -Force;" ^
            "Remove-Item -Path $env:EMBED_ZIP_TMP -Force -ErrorAction SilentlyContinue;"

        if exist "!PY_TARGET_DIR!\python.exe" (
            echo [OK] Micro-kernel extracted successfully!
            echo [*] Configuring private environment and package directory...

            REM Configure python310._pth to enable site-packages and project root path
            powershell -NoProfile -ExecutionPolicy Bypass -Command ^
                "$pth = Join-Path $env:PY_TARGET_DIR 'python310._pth';" ^
                "@('python310.zip', '.', '..', 'Lib\site-packages', 'import site') | Set-Content -Path $pth -Encoding Ascii;" ^
                "$sp = Join-Path $env:PY_TARGET_DIR 'Lib\site-packages';" ^
                "if (-not (Test-Path $sp)) { New-Item -ItemType Directory -Path $sp -Force | Out-Null };"

            REM Download and bootstrap pip
            echo [*] Bootstrapping pip engine for micro-kernel (approx. 2 MB)...
            set "GET_PIP_TMP=%TEMP%\get_pip_%RANDOM%.py"
            powershell -NoProfile -ExecutionPolicy Bypass -Command ^
                "try { [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]3072; } catch {}" ^
                "$pip_urls = @(" ^
                "    'https://registry.npmmirror.com/-/binary/pip/get-pip.py'," ^
                "    'https://mirrors.aliyun.com/pypi/get-pip.py'," ^
                "    'https://bootstrap.pypa.io/get-pip.py'" ^
                ");" ^
                "$out = $env:GET_PIP_TMP;" ^
                "foreach ($u in $pip_urls) {" ^
                "    try {" ^
                "        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {" ^
                "            & curl.exe -L -k --ssl-no-revoke -s --connect-timeout 15 $u -o $out;" ^
                "        } else {" ^
                "            (New-Object System.Net.WebClient).DownloadFile($u, $out);" ^
                "        }" ^
                "        if ((Test-Path $out) -and ((Get-Item $out).Length -gt 1000000)) { break; }" ^
                "    } catch {}" ^
                "}"

            if exist "!GET_PIP_TMP!" (
                "!PY_TARGET_DIR!\python.exe" "!GET_PIP_TMP!" --no-warn-script-location --no-setuptools --no-wheel -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1
                del /f /q "!GET_PIP_TMP!" >nul 2>&1
            )

            REM Check VC++ MSVCP140.dll and copy if needed
            if not exist "!PY_TARGET_DIR!\msvcp140.dll" (
                if exist "C:\Windows\System32\msvcp140.dll" (
                    copy /y "C:\Windows\System32\msvcp140*.dll" "!PY_TARGET_DIR!\" >nul 2>&1
                )
            )

            set "PYTHON_EXE=!PY_TARGET_DIR!\python.exe"
            set "IS_PORTABLE_ENV=1"
            echo [OK] Portable Python micro-kernel successfully deployed: !PYTHON_EXE!
        )
    )
)

if not defined PYTHON_EXE (
    echo.
    echo ==============================================================================
    echo [ERROR] Failed to detect or automatically deploy Python runtime.
    echo ==============================================================================
    echo Please ensure your computer is connected to the internet, or install Python 3.8+:
    echo https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during manual installation.
    echo.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

echo [OK] Selected Python interpreter: !PYTHON_EXE!

REM ------------------------------------------------------------------------------
REM Step 2/5: Initializing local isolated virtual environment
REM ------------------------------------------------------------------------------
echo.
echo [Step 2/5] Initializing isolated virtual environment...

if "!IS_PORTABLE_ENV!"=="1" (
    set "RUN_PYTHON=!PYTHON_EXE!"
    echo [OK] Using dedicated portable Python runtime directly: !RUN_PYTHON!
) else if "!IS_CONDA_ENV!"=="1" (
    set "RUN_PYTHON=!PYTHON_EXE!"
    echo [OK] Using isolated Conda environment directly: !RUN_PYTHON!
) else (
    if not exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
        echo [*] Creating local virtual environment in .venv...
        "!PYTHON_EXE!" -m venv "%SCRIPT_DIR%\.venv"
    )

    if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
        set "RUN_PYTHON=%SCRIPT_DIR%\.venv\Scripts\python.exe"
        echo [OK] Local virtual environment ready: .venv
    ) else (
        set "RUN_PYTHON=!PYTHON_EXE!"
        echo [NOTE] Using dedicated Python runtime directly.
    )
)

REM ------------------------------------------------------------------------------
REM Step 3/5: Upgrading pip and setting up mirror sources
REM ------------------------------------------------------------------------------
echo.
echo [Step 3/5] Configuring pip package manager (Tencent / Tsinghua mirror)...
"!RUN_PYTHON!" -m pip install --upgrade pip -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1

REM ------------------------------------------------------------------------------
REM Step 4/5: Installing core dependencies (PyQt5, OpenCV, Pillow, lxml, pyyaml, numpy)
REM ------------------------------------------------------------------------------
echo.
echo [Step 4/5] Checking and installing core dependencies (PyQt5, OpenCV, Pillow, lxml, pyyaml, numpy)...

REM Fast check: If already present (e.g. offline portable bundle), skip download!
"!RUN_PYTHON!" -c "import PyQt5, cv2, PIL, lxml, yaml, numpy" >nul 2>&1
if !errorlevel! EQU 0 (
    echo [OK] All core dependencies are already pre-installed and verified!
    goto verify_step
)

echo [*] Installing GUI and XML parsers (PyQt5, lxml, Pillow, pyyaml, yamlloader)...
"!RUN_PYTHON!" -m pip install "pyqt5>=5.15.0" "lxml>=4.9.0" "Pillow>=9.5.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" -i !PIP_INDEX! !TRUSTED_HOST!
if errorlevel 1 (
    echo [Retry] Retrying GUI dependencies with Aliyun mirror...
    "!RUN_PYTHON!" -m pip install "pyqt5>=5.15.0" "lxml>=4.9.0" "Pillow>=9.5.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
    if errorlevel 1 (
        echo [ERROR] Failed to install core GUI and XML dependencies.
        if "%IS_AUTO_MODE%"=="0" pause
        exit /b 1
    )
)

echo [*] Installing Computer Vision engine (OpenCV-Headless and NumPy)...
"!RUN_PYTHON!" -m pip install "opencv-python-headless>=4.7.0" "numpy>=1.23.0" -i !PIP_INDEX! !TRUSTED_HOST!
if errorlevel 1 (
    echo [Retry] Retrying with Tsinghua mirror...
    "!RUN_PYTHON!" -m pip install "opencv-python-headless>=4.7.0" "numpy>=1.23.0" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
)

:verify_step
REM ------------------------------------------------------------------------------
REM Step 5/5: Verifying runtime dependencies and self-test
REM ------------------------------------------------------------------------------
echo.
echo [Step 5/5] Performing runtime verification and self-test...
"!RUN_PYTHON!" -c "import PyQt5, cv2, PIL, lxml, yaml, numpy; print('[OK] All core dependencies verified successfully!')"
if errorlevel 1 (
    echo.
    echo ==============================================================================
    echo [ERROR] Dependency verification encountered issues! Missing modules detected:
    echo ==============================================================================
    "!RUN_PYTHON!" -c "import sys; mods = ['PyQt5', 'cv2', 'PIL', 'lxml', 'yaml', 'numpy']; errs = 0; [exec('try:\n __import__(m)\n print(f\"  [OK] {m}\")\nexcept Exception as e:\n print(f\"  [FAILED] {m} -> {e}\"); errs += 1') for m in mods]; sys.exit(errs)"
    echo.
    echo Please check your network connection and retry setup_env.bat.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

REM ------------------------------------------------------------------------------
REM Create Desktop and Start Menu Shortcuts
REM ------------------------------------------------------------------------------
set "TARGET_BAT=%SCRIPT_DIR%\Start_LabelImg2.bat"
if exist "%SCRIPT_DIR%\img\app.ico" (
    set "ICON_FILE=%SCRIPT_DIR%\img\app.ico"
) else (
    set "ICON_FILE=%SCRIPT_DIR%\img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$dirs = @([Environment]::GetFolderPath('Desktop'), \"$env:USERPROFILE\Desktop\", \"$env:USERPROFILE\OneDrive\Desktop\");" ^
    "foreach ($d in $dirs) { if ($d -and (Test-Path $d)) { try { $s = $ws.CreateShortcut((Join-Path $d 'LabelImg2.lnk')); $s.TargetPath = $env:TARGET_BAT; $s.WorkingDirectory = $env:SCRIPT_DIR; $s.IconLocation = $env:ICON_FILE + ',0'; $s.Description = 'LabelImg2'; $s.Save(); } catch {} } };" ^
    "$sm = [Environment]::GetFolderPath('Programs');" ^
    "if ($sm -and (Test-Path $sm)) { try { $s2 = $ws.CreateShortcut((Join-Path $sm 'LabelImg2.lnk')); $s2.TargetPath = $env:TARGET_BAT; $s2.WorkingDirectory = $env:SCRIPT_DIR; $s2.IconLocation = $env:ICON_FILE + ',0'; $s2.Description = 'LabelImg2'; $s2.Save(); } catch {} }" >nul 2>&1

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
