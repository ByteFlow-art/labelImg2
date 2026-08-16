@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 - 智能启动器 (Smart Launcher)
REM   功能：自动定位运行环境，若首次运行无环境则无缝引导自动化搭建
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

title LabelImg2 - AI 智能计算机视觉标注工作台

set "PYTHON_CMD="

REM 1. 优先检测本地虚拟环境 .venv
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    goto :RUN_APP
)

REM 2. 检查便携式 Python 运行环境 python_embed
if exist "%SCRIPT_DIR%\python_embed\python.exe" (
    set "PYTHON_CMD=%SCRIPT_DIR%\python_embed\python.exe"
    goto :RUN_APP
)

REM 3. 检查常见 Conda 环境中的 labelimg2
set "CONDA_ACTIVATE="
for %%P in (
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\ProgramData\anaconda3\Scripts\activate.bat"
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
    "C:\Miniconda3\Scripts\activate.bat"
    "C:\Anaconda3\Scripts\activate.bat"
    "D:\Anaconda3\Scripts\activate.bat"
    "D:\miniconda3\Scripts\activate.bat"
) do (
    if not defined CONDA_ACTIVATE if exist "%%~P" set "CONDA_ACTIVATE=%%~P"
)

if defined CONDA_ACTIVATE (
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where python 2^>nul') do (
            if not defined PYTHON_CMD set "PYTHON_CMD=%%~fI"
        )
        if defined PYTHON_CMD (
            set "QT_QPA_PLATFORM_PLUGIN_PATH=%CONDA_PREFIX%\Library\plugins\platforms"
            goto :RUN_APP
        )
    )
)

REM 4. 检查当前系统默认 python 是否满足依赖
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_CMD set "PYTHON_CMD=%%~fI"
)

if defined PYTHON_CMD (
    "!PYTHON_CMD!" -c "import PyQt5, ultralytics" >nul 2>&1
    if not errorlevel 1 goto :RUN_APP
)

REM 5. 如果未找到任何可用环境，提示并自动执行 setup_env.bat
echo.
echo ==============================================================================
echo [提示] 首次启动未检测到 LabelImg2 运行环境，正在启动自动安装向导...
echo ==============================================================================
echo.
call "%SCRIPT_DIR%\setup_env.bat"
exit /b 0

:RUN_APP
echo [LabelImg2] 正在启动标注工作台...
start "" "!PYTHON_CMD!" "%SCRIPT_DIR%\labelImg.py" %*

endlocal
exit /b 0
