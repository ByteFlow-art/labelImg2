@echo off
chcp 65001 >nul
setlocal

REM ==============================================================================
REM   LabelImg2 - 官方安装引导器 (自动解除 Windows SmartScreen 拦截并启动安装)
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [*] 正在初始化 LabelImg2 安装程序...

REM 自动解除从浏览器下载文件附带的 Mark-of-the-Web (MOTW) 拦截标记
powershell -NoProfile -Command "Get-ChildItem -Path '%SCRIPT_DIR%' -Recurse | Unblock-File" >nul 2>&1

if exist "%SCRIPT_DIR%LabelImg2_Setup_v1.0.0.exe" (
    start "" "%SCRIPT_DIR%LabelImg2_Setup_v1.0.0.exe"
    exit /b 0
)

if exist "%SCRIPT_DIR%dist\LabelImg2_Setup_v1.0.0.exe" (
    start "" "%SCRIPT_DIR%dist\LabelImg2_Setup_v1.0.0.exe"
    exit /b 0
)

echo [提示] 正在启动安装向导...
python "%SCRIPT_DIR%installer_gui.py"

endlocal
exit /b 0
