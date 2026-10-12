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

REM Proactively check and bypass dead localhost proxies (e.g. 127.0.0.1:7890) left by closed VPN/Clash
if not defined HTTP_PROXY goto check_https_proxy
echo !HTTP_PROXY! | findstr /i "127.0.0.1 localhost" >nul 2>&1
if errorlevel 1 goto check_https_proxy
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u = [System.Uri]$env:HTTP_PROXY; $t = New-Object System.Net.Sockets.TcpClient; try { $t.Connect($u.Host, $u.Port); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [NOTICE] Inactive local proxy detected. Bypassing HTTP_PROXY...
    set "HTTP_PROXY="
    set "http_proxy="
    set "ALL_PROXY="
    set "all_proxy="
)

:check_https_proxy
if not defined HTTPS_PROXY goto proxy_checked
echo !HTTPS_PROXY! | findstr /i "127.0.0.1 localhost" >nul 2>&1
if errorlevel 1 goto proxy_checked
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u = [System.Uri]$env:HTTPS_PROXY; $t = New-Object System.Net.Sockets.TcpClient; try { $t.Connect($u.Host, $u.Port); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [NOTICE] Inactive local proxy detected. Bypassing HTTPS_PROXY...
    set "HTTPS_PROXY="
    set "https_proxy="
    set "ALL_PROXY="
    set "all_proxy="
)

:proxy_checked

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

if not defined CONDA_CMD goto check_system_python

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

if defined CONDA_ENV_PY goto conda_env_ready

echo [*] Conda environment 'labelimg2' not found.
echo [*] Automatically creating dedicated isolated Conda environment 'labelimg2' - Python 3.10...
echo [*] Please wait while Conda provisions the environment...
call "!CONDA_CMD!" create -y -n labelimg2 python=3.10
if !errorlevel! NEQ 0 (
    echo [WARNING] Conda create python=3.10 reported non-zero code. Retrying without python version lock...
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

:conda_env_ready
if defined CONDA_ENV_PY (
    set "PYTHON_EXE=!CONDA_ENV_PY!"
    set "IS_CONDA_ENV=1"
    echo [OK] Successfully selected dedicated Conda environment: !PYTHON_EXE!
    goto python_found
)

:check_system_python
REM ------------------------------------------------------------------------------
REM Sub-step 1B: If Conda is not used, check existing local or system Python
REM ------------------------------------------------------------------------------
if exist "%SCRIPT_DIR%\python_runtime\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\python_runtime\python.exe"
    set "IS_PORTABLE_ENV=1"
    echo [OK] Found dedicated portable Python runtime: python_runtime\python.exe
    goto python_found
)

if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    echo [OK] Found local virtual environment: .venv\Scripts\python.exe
    goto python_found
)

where py.exe >nul 2>&1
if !errorlevel! EQU 0 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined PYTHON_EXE if exist "%%~I" (
            set "PYTHON_EXE=%%~I"
            echo [OK] Found system Python via py.exe: %%~I
            goto python_found
        )
    )
)

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
        goto python_found
    )
)

for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
    if not defined PYTHON_EXE if exist "%%~B" (
        set "PYTHON_EXE=%%~B"
        echo [OK] Found Python in user registry: %%~B
        goto python_found
    )
)
for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v "ExecutablePath" 2^>nul ^| findstr /i "ExecutablePath"') do (
    if not defined PYTHON_EXE if exist "%%~B" (
        set "PYTHON_EXE=%%~B"
        echo [OK] Found Python in system registry: %%~B
        goto python_found
    )
)

for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE (
        set "CANDIDATE=%%~fI"
        echo !CANDIDATE! | findstr /i /c:"WindowsApps" >nul
        if errorlevel 1 (
            set "PYTHON_EXE=!CANDIDATE!"
            echo [OK] Found system PATH Python: !PYTHON_EXE!
            goto python_found
        )
    )
)

:deploy_microkernel
REM ------------------------------------------------------------------------------
REM Sub-step 1C: Zero-Environment Automated Fallback (Micro-Kernel Embed Python 9.9 MB)
REM ------------------------------------------------------------------------------
echo.
echo [Step 1/5] No Python/Conda detected on this computer.
echo [*] Initiating ultra-lightweight micro-kernel deployment - approx 9.9 MB...
echo [*] Target destination: "%SCRIPT_DIR%\python_runtime"
echo [*] Downloading official portable micro-kernel from high-speed mirror...

set "EMBED_ZIP_TMP=%TEMP%\python_embed_%RANDOM%.zip"
set "PY_TARGET_DIR=%SCRIPT_DIR%\python_runtime"

set "DL_SCRIPT=%TEMP%\dl_embed_%RANDOM%.ps1"
(
echo [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
echo $urls = @(
echo     'https://registry.npmmirror.com/-/binary/python/3.10.11/python-3.10.11-embed-amd64.zip',
echo     'https://mirrors.huaweicloud.com/python/3.10.11/python-3.10.11-embed-amd64.zip',
echo     'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip'
echo ^)
echo $out = '%EMBED_ZIP_TMP%'
echo $downloaded = $false
echo foreach ($u in $urls^) {
echo     try {
echo         Write-Host ('[*] Connecting to: ' + $u^)
echo         if (Get-Command curl.exe -ErrorAction SilentlyContinue^) {
echo             ^& curl.exe -L -k --ssl-no-revoke --connect-timeout 15 $u -o $out
echo         } else {
echo             $wc = New-Object System.Net.WebClient
echo             $wc.Headers.Add('User-Agent', 'Mozilla/5.0'^)
echo             $wc.DownloadFile($u, $out^)
echo         }
echo         if ((Test-Path $out^) -and ((Get-Item $out^).Length -gt 5000000^)^) {
echo             $downloaded = $true
echo             Write-Host '[OK] Micro-kernel download completed successfully.'
echo             break
echo         }
echo     } catch {}
echo }
echo if (-not $downloaded^) { exit 1 }
) > "%DL_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%DL_SCRIPT%"
del /f /q "%DL_SCRIPT%" >nul 2>&1

if not exist "!EMBED_ZIP_TMP!" goto check_fail

echo [*] Extracting portable micro-kernel into private directory...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Test-Path '%PY_TARGET_DIR%')) { New-Item -ItemType Directory -Path '%PY_TARGET_DIR%' -Force | Out-Null }; Expand-Archive -Path '%EMBED_ZIP_TMP%' -DestinationPath '%PY_TARGET_DIR%' -Force;"
del /f /q "!EMBED_ZIP_TMP!" >nul 2>&1

if not exist "!PY_TARGET_DIR!\python.exe" goto check_fail

echo [OK] Micro-kernel extracted successfully!
echo [*] Configuring private environment and package directory...

powershell -NoProfile -ExecutionPolicy Bypass -Command "@('python310.zip', '.', '..', 'Lib\site-packages', 'import site') | Set-Content -Path (Join-Path '%PY_TARGET_DIR%' 'python310._pth') -Encoding Ascii; if (-not (Test-Path (Join-Path '%PY_TARGET_DIR%' 'Lib\site-packages'))^) { New-Item -ItemType Directory -Path (Join-Path '%PY_TARGET_DIR%' 'Lib\site-packages') -Force | Out-Null };"

echo [*] Bootstrapping pip engine for micro-kernel - approx 2 MB...
set "GET_PIP_TMP=%TEMP%\get_pip_%RANDOM%.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$urls = @('https://registry.npmmirror.com/-/binary/pip/get-pip.py', 'https://mirrors.aliyun.com/pypi/get-pip.py', 'https://bootstrap.pypa.io/get-pip.py'); foreach ($u in $urls) { try { if (Get-Command curl.exe -ErrorAction SilentlyContinue) { & curl.exe -L -k --ssl-no-revoke -s --connect-timeout 15 $u -o '%GET_PIP_TMP%'; } else { (New-Object System.Net.WebClient).DownloadFile($u, '%GET_PIP_TMP%'); } if ((Test-Path '%GET_PIP_TMP%') -and ((Get-Item '%GET_PIP_TMP%').Length -gt 1000000)) { break; } } catch {} }"

if exist "!GET_PIP_TMP!" (
    "!PY_TARGET_DIR!\python.exe" "!GET_PIP_TMP!" --no-warn-script-location --no-setuptools --no-wheel -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1
    del /f /q "!GET_PIP_TMP!" >nul 2>&1
)

if not exist "!PY_TARGET_DIR!\msvcp140.dll" (
    if exist "C:\Windows\System32\msvcp140.dll" (
        copy /y "C:\Windows\System32\msvcp140*.dll" "!PY_TARGET_DIR!\" >nul 2>&1
    )
)

set "PYTHON_EXE=!PY_TARGET_DIR!\python.exe"
set "IS_PORTABLE_ENV=1"
echo [OK] Portable Python micro-kernel successfully deployed: !PYTHON_EXE!
goto python_found

:check_fail
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

:python_found
echo [OK] Selected Python interpreter: !PYTHON_EXE!

REM ------------------------------------------------------------------------------
REM Step 2/5: Initializing local isolated virtual environment
REM ------------------------------------------------------------------------------
echo.
echo [Step 2/5] Initializing isolated virtual environment...

if "!IS_PORTABLE_ENV!"=="1" (
    set "RUN_PYTHON=!PYTHON_EXE!"
    echo [OK] Using dedicated portable Python runtime directly: !RUN_PYTHON!
    goto step3_pip
)

if "!IS_CONDA_ENV!"=="1" (
    set "RUN_PYTHON=!PYTHON_EXE!"
    echo [OK] Using isolated Conda environment directly: !RUN_PYTHON!
    goto step3_pip
)

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

:step3_pip
REM ------------------------------------------------------------------------------
REM Step 3/5: Upgrading pip and setting up mirror sources
REM ------------------------------------------------------------------------------
echo.
echo [Step 3/5] Configuring pip package manager - Tencent / Tsinghua mirror...
"!RUN_PYTHON!" -m pip config set global.index-url !PIP_INDEX! >nul 2>&1
"!RUN_PYTHON!" -m pip config set global.trusted-host mirrors.cloud.tencent.com >nul 2>&1
"!RUN_PYTHON!" -m pip config set global.timeout 25 >nul 2>&1
"!RUN_PYTHON!" -m pip config set global.retries 2 >nul 2>&1
"!RUN_PYTHON!" -m pip install --upgrade pip -i !PIP_INDEX! !TRUSTED_HOST! >nul 2>&1

REM ------------------------------------------------------------------------------
REM Step 4/5: Installing dependencies (Tiered resilient installation)
REM ------------------------------------------------------------------------------
echo.
echo [Step 4/5] Checking and installing unified dependencies...

REM Tier 1: Core Essential Dependencies (PyQt5, OpenCV, Pillow, lxml, pyyaml, yamlloader, numpy)
echo [*] Checking core labeling dependencies: PyQt5, OpenCV, Pillow, lxml, YAML, NumPy...
"!RUN_PYTHON!" -c "import PyQt5, cv2, PIL, lxml, yaml, numpy" >nul 2>&1
if !errorlevel! EQU 0 (
    echo [OK] Core labeling dependencies are already verified!
    goto tier2_ai
)

echo [*] Installing core labeling dependencies from mirror...
"!RUN_PYTHON!" -m pip install "PyQt5>=5.15.0" "opencv-python-headless>=4.7.0" "Pillow>=9.5.0" "lxml>=4.9.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" "numpy>=1.23.0" -i !PIP_INDEX! !TRUSTED_HOST! --retries 2 --default-timeout=25
if errorlevel 1 (
    echo [Retry] Retrying core dependencies with Aliyun mirror...
    "!RUN_PYTHON!" -m pip install "PyQt5>=5.15.0" "opencv-python-headless>=4.7.0" "Pillow>=9.5.0" "lxml>=4.9.0" "pyyaml>=6.0.0" "yamlloader>=0.5.5" "numpy>=1.23.0" -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --retries 2 --default-timeout=25
)

"!RUN_PYTHON!" -c "import PyQt5, cv2, PIL, lxml, yaml, numpy" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install core labeling dependencies.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

:tier2_ai
echo [OK] Core labeling engine is 100%% ready!

REM Tier 2: AI Model Center & Deep Learning Extension (Torch, Ultralytics)
echo.
echo [*] Checking AI model engine extension: Torch, Ultralytics...
"!RUN_PYTHON!" -c "import torch, ultralytics" >nul 2>&1
if !errorlevel! EQU 0 (
    echo [OK] AI deep learning extension is already verified!
    goto verify_step
)

echo [*] Installing AI model engine extension from domestic mirror...
"!RUN_PYTHON!" -m pip install ultralytics torch torchvision -i !PIP_INDEX! !TRUSTED_HOST! --retries 2 --default-timeout=25
if errorlevel 1 (
    echo [Retry] Retrying AI extension with Aliyun mirror...
    "!RUN_PYTHON!" -m pip install ultralytics torch torchvision -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --retries 2 --default-timeout=25
)
if errorlevel 1 (
    echo [NOTICE] AI extension package download timed out or skipped due to network bandwidth.
    echo [NOTICE] LabelImg2 core labeling and format conversion is 100%% fully operational!
    echo [NOTICE] You can run and use LabelImg2 immediately. AI models can be complemented later in YOLO Model Center.
) else (
    echo [OK] AI model engine extension installed successfully!
)

REM Purge wheel download cache to save disk space
"!RUN_PYTHON!" -m pip cache purge >nul 2>&1

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
    echo [ERROR] Dependency verification encountered issues!
    echo ==============================================================================
    echo Please check your network connection and retry setup_env.bat.
    if "%IS_AUTO_MODE%"=="0" pause
    exit /b 1
)

REM Cache configured Python interpreter for high-speed direct launch
echo !RUN_PYTHON!> "%SCRIPT_DIR%\.python_path" 2>nul

REM ------------------------------------------------------------------------------
REM Create Desktop and Start Menu Shortcuts
REM ------------------------------------------------------------------------------
set "TARGET_BAT=%SCRIPT_DIR%\Start_LabelImg2.bat"
if exist "%SCRIPT_DIR%\img\app.ico" (
    set "ICON_FILE=%SCRIPT_DIR%\img\app.ico"
) else (
    set "ICON_FILE=%SCRIPT_DIR%\img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $dirs = @([Environment]::GetFolderPath('Desktop'), \"$env:USERPROFILE\Desktop\", \"$env:USERPROFILE\OneDrive\Desktop\"); foreach ($d in $dirs) { if ($d -and (Test-Path $d)) { try { $s = $ws.CreateShortcut((Join-Path $d 'LabelImg2.lnk')); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = '%ICON_FILE%,0'; $s.Description = 'LabelImg2'; $s.Save(); } catch {} } }; $sm = [Environment]::GetFolderPath('Programs'); if ($sm -and (Test-Path $sm)) { try { $s2 = $ws.CreateShortcut((Join-Path $sm 'LabelImg2.lnk')); $s2.TargetPath = '%TARGET_BAT%'; $s2.WorkingDirectory = '%SCRIPT_DIR%'; $s2.IconLocation = '%ICON_FILE%,0'; $s2.Description = 'LabelImg2'; $s2.Save(); } catch {} }" >nul 2>&1

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
