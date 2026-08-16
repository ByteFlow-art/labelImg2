@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 Next-Gen 核心启动器 (Main Application Launcher)
REM   兼容所有目录路径，自动寻找已配置的 Conda / 本地环境 / 全局 Python 并启动
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

title LabelImg2 - AI 智能计算机视觉标注工作台

set "ENV_NAME=labelimg2"
set "APP_FILE=labelImg.py"

echo.
echo ==============================================================================
echo            LabelImg2 Next-Gen 计算机视觉标注工作台 - 启动中...
echo ==============================================================================
echo.

if not exist "%SCRIPT_DIR%\%APP_FILE%" (
    echo [错误] 未在当前目录下找到核心启动文件: %APP_FILE%
    echo 请确认启动器位于 LabelImg2 项目根目录中。
    pause
    exit /b 1
)

set "PYTHON_EXE="

REM 1. 优先检测本地虚拟环境 (.venv)
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    echo [OK] 正在使用项目隔离虚拟环境 (.venv)...
    goto :START_APP
)

REM 2. 优先检测便携式 Python (python_embed)
if exist "%SCRIPT_DIR%\python_embed\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\python_embed\python.exe"
    echo [OK] 正在使用便携式 Python 运行环境...
    goto :START_APP
)

REM 3. 自动探测 Conda 管理器与 labelimg2 专属环境
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
    echo [OK] 正在激活 Conda 运行环境: %ENV_NAME% ...
    call "!CONDA_ACTIVATE!" "%ENV_NAME%" >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where python 2^>nul') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
        )
        if defined PYTHON_EXE (
            if defined CONDA_PREFIX (
                set "QT_QPA_PLATFORM_PLUGIN_PATH=%CONDA_PREFIX%\Library\plugins\platforms"
            )
            echo [OK] 已成功挂载 Conda 环境: !PYTHON_EXE!
            goto :START_APP
        )
    )
)

REM 4. 检测系统全局 Python
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
)

if defined PYTHON_EXE (
    "!PYTHON_EXE!" -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] 正在使用全局 Python: !PYTHON_EXE!
        goto :START_APP
    )
)

REM 5. 若未检测到任何可用环境，自动唤起环境初始化向导
echo.
echo [提示] 检测到当前系统尚未初始化 LabelImg2 依赖环境。
echo 正在自动调用一键安装向导 (setup_env.bat)...
echo.
call "%SCRIPT_DIR%\setup_env.bat"
exit /b 0

:START_APP
echo [OK] 正在进入 LabelImg2 工作台...
start "" "!PYTHON_EXE!" "%SCRIPT_DIR%\%APP_FILE%" %*
set "APP_EXIT_CODE=%ERRORLEVEL%"

endlocal
exit /b %APP_EXIT_CODE%
