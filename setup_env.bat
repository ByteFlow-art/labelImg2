@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==============================================================================
REM   LabelImg2 - 一键全自动环境配置与初始化向导 (Automated Environment Setup)
REM   适用场景：全新裸机系统、无Python/Conda环境、或重新初始化依赖环境
REM ==============================================================================

echo.
echo ==============================================================================
echo            LabelImg2 Next-Gen 计算机视觉标注工作台 - 环境初始化向导
echo ==============================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_EXE="
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"

echo [步骤 1/5] 正在检测系统 Python / Conda 运行环境...

REM 1. 检查本地 .venv 虚拟环境
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
    echo [OK] 检测到项目本地虚拟环境: .venv\Scripts\python.exe
    goto :INSTALL_DEPS
)

REM 2. 检查常见 Conda 安装路径与激活脚本
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
    echo [OK] 检测到 Conda 管理器: !CONDA_ACTIVATE!
    echo [步骤 2/5] 正在激活/创建 Conda 环境: labelimg2 ...
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where python 2^>nul') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
        )
        if defined PYTHON_EXE (
            echo [OK] 已成功激活 Conda 环境 [labelimg2]
            goto :INSTALL_DEPS
        )
    )
    REM 如果没有 labelimg2 环境，尝试创建
    echo [*] 正在创建新的 Conda 环境 [labelimg2] (Python 3.10)...
    call "!CONDA_ACTIVATE!" base
    call conda create -n labelimg2 python=3.10 -y
    call "!CONDA_ACTIVATE!" labelimg2
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
    )
    if defined PYTHON_EXE goto :INSTALL_DEPS
)

REM 3. 检查系统全局 python
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
)

if defined PYTHON_EXE (
    echo [OK] 检测到系统全局 Python: !PYTHON_EXE!
    echo [步骤 2/5] 正在创建项目本地隔离虚拟环境 (.venv)...
    "!PYTHON_EXE!" -m venv "%SCRIPT_DIR%\.venv"
    if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
        echo [OK] 本地虚拟环境创建成功: .venv
        goto :INSTALL_DEPS
    )
)

REM 4. 若未检测到任何 Python，提供一键便携式 Python 下载安装提示
echo.
echo [警告] 未在当前系统中检测到 Python 3.8+ 或 Conda 环境！
echo.
echo 请选择安装方式：
echo   [1] 自动下载并解压便携式 Python 3.10 运行环境 (推荐，纯绿色无污染)
echo   [2] 退出并自行安装 Python (https://www.python.org/downloads/)
echo.
set /p USER_CHOICE="请输入选项 [1 或 2，默认 1]: "
if "%USER_CHOICE%"=="" set "USER_CHOICE=1"

if "%USER_CHOICE%"=="1" (
    echo [*] 正在下载便携式 Python 运行环境，请稍候...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://npmmirror.com/mirrors/python/3.10.11/python-3.10.11-embed-amd64.zip', 'python_embed.zip')"
    if exist "python_embed.zip" (
        powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath 'python_embed' -Force"
        del python_embed.zip
        echo import site >> python_embed\python310._pth
        echo [*] 正在下载 pip 引导工具...
        powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'python_embed\get-pip.py')"
        python_embed\python.exe python_embed\get-pip.py --no-warn-script-location -i !PIP_INDEX_URL!
        if exist "python_embed\Scripts\pip.exe" (
            set "PYTHON_EXE=%SCRIPT_DIR%\python_embed\python.exe"
            echo [OK] 便携式 Python 环境部署成功！
            goto :INSTALL_DEPS
        )
    )
    echo [错误] 自动下载便携式 Python 失败，请检查网络连接。
)

echo.
echo [提示] 请安装 Python 3.8 ~ 3.11 并将其勾选加入环境变量 PATH，然后重新运行本脚本。
pause
exit /b 1

:INSTALL_DEPS
echo.
echo [步骤 3/5] 正在升级 pip 并配置国内极速镜像源...
"!PYTHON_EXE!" -m pip install --upgrade pip -i !PIP_INDEX_URL! >nul 2>&1

echo.
echo [步骤 4/5] 正在安装核心依赖包 (PyQt5, Ultralytics, PyTorch, OpenCV, lxml 等)...
echo [*] 使用清华大学镜像源高速安装中，请稍候...
"!PYTHON_EXE!" -m pip install -r requirements.txt -i !PIP_INDEX_URL!

if errorlevel 1 (
    echo.
    echo [重试] 尝试备用镜像源安装...
    "!PYTHON_EXE!" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
)

echo.
echo [步骤 5/5] 正在验证 LabelImg2 运行环境完整性...
"!PYTHON_EXE!" -c "import PyQt5, torch, ultralytics, cv2, PIL, lxml, yaml; print('[OK] 所有核心依赖库加载验证通过！')"

if errorlevel 1 (
    echo.
    echo [警告] 部分依赖加载异常，请检查上述错误信息。
    pause
    exit /b 1
)

echo.
echo ==============================================================================
echo   [成功] LabelImg2 环境部署已全部完成！
echo   现在您可以直接双击 [Launch_LabelImg2.bat] 启动标注工作台。
echo ==============================================================================
echo.

REM 询问是否立即启动
set /p LAUNCH_NOW="是否立即启动 LabelImg2？(Y/N，默认 Y): "
if /i "%LAUNCH_NOW%"=="" set "LAUNCH_NOW=Y"
if /i "%LAUNCH_NOW%"=="Y" (
    start "" "%SCRIPT_DIR%\Launch_LabelImg2.bat"
)

endlocal
exit /b 0
