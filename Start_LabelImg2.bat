@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
title LabelImg2

set "APP_FILE=labelImg.py"

if not exist "%SCRIPT_DIR%%APP_FILE%" (
    echo [错误] 未在当前目录下找到主程序文件: %APP_FILE%
    echo 脚本所在路径: %SCRIPT_DIR%
    pause
    exit /b 1
)

:: 1. 优先检测项目本地虚拟环境 (.venv)
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        start "" "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%%APP_FILE%" %*
        exit /b 0
    )
)

:: 2. 检测本地便携式 Python 环境 (python_embed)
if exist "%SCRIPT_DIR%python_embed\python.exe" (
    "%SCRIPT_DIR%python_embed\python.exe" -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        start "" "%SCRIPT_DIR%python_embed\python.exe" "%SCRIPT_DIR%%APP_FILE%" %*
        exit /b 0
    )
)

:: 3. 检测常见 Conda 管理器与 labelimg2 虚拟环境
set "CONDA_ACTIVATE="
for %%P in (
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\ProgramData\anaconda3\Scripts\activate.bat"
    "C:\Miniconda3\Scripts\activate.bat"
    "C:\Anaconda3\Scripts\activate.bat"
    "D:\Anaconda3\Scripts\activate.bat"
    "D:\miniconda3\Scripts\activate.bat"
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
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
    if not errorlevel 1 (
        if defined CONDA_PREFIX (
            set "QT_QPA_PLATFORM_PLUGIN_PATH=%CONDA_PREFIX%\Library\plugins\platforms"
            start "" "!CONDA_PREFIX!\python.exe" "%SCRIPT_DIR%%APP_FILE%" %*
            exit /b 0
        )
    )
)

:: 4. 检测系统全局 Python 环境
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    "%%~fI" -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        start "" "%%~fI" "%SCRIPT_DIR%%APP_FILE%" %*
        exit /b 0
    )
)

:: 5. 首次启动或未配置环境：自动调用环境初始化向导
echo ==============================================================================
echo                 LabelImg2 首次启动 - 正在自动配置运行环境
echo ==============================================================================
echo.
if exist "%SCRIPT_DIR%setup_env.bat" (
    call "%SCRIPT_DIR%setup_env.bat" --auto
    if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
        start "" "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%%APP_FILE%" %*
        exit /b 0
    )
) else (
    echo [错误] 缺失环境配置文件 setup_env.bat，请确保项目文件完整。
    pause
)

exit /b 0

