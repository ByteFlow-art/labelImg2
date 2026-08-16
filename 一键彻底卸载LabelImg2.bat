@echo off
chcp 65001 >nul
setlocal

REM ==============================================================================
REM   LabelImg2 - 一键彻底卸载与环境清理脚本
REM   功能：彻底清理桌面快捷方式、Python 虚拟环境 (.venv / python_embed)、模型与缓存
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================================
echo                 LabelImg2 - 一键彻底卸载与环境清理工具
echo ==============================================================================
echo.
echo [警告] 本操作将彻底清理以下全部内容：
echo   1. 电脑桌面的 [LabelImg2] 快捷方式
echo   2. 本目录下的 Python 虚拟环境与依赖 (.venv / python_embed)
echo   3. 所有运行缓存、编译产物与模型缓存
echo.

set /p CONFIRM="确定要彻底卸载并清理全部环境吗？(输入 Y 确认，其他取消): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo [已取消] 卸载操作已终止。
    pause
    exit /b 0
)

echo.
echo [*] 正在删除桌面快捷方式...
powershell -NoProfile -Command "$Desktop = [Environment]::GetFolderPath('Desktop'); Remove-Item -Path ($Desktop + '\LabelImg2.lnk') -Force -ErrorAction SilentlyContinue;" >nul 2>&1

echo [*] 正在清理 Python 虚拟环境 (.venv)...
if exist "%SCRIPT_DIR%.venv" (
    rd /s /q "%SCRIPT_DIR%.venv" >nul 2>&1
)

echo [*] 正在清理便携式 Python 运行环境 (python_embed)...
if exist "%SCRIPT_DIR%python_embed" (
    rd /s /q "%SCRIPT_DIR%python_embed" >nul 2>&1
)

echo [*] 正在清理编译构建与临时缓存 (build / dist / runs / __pycache__)...
for %%D in (build dist runs __pycache__) do (
    if exist "%SCRIPT_DIR%%%D" rd /s /q "%SCRIPT_DIR%%%D" >nul 2>&1
)

echo.
echo ==============================================================================
echo   [成功] LabelImg2 虚拟环境、桌面图标与全部运行缓存已彻底清理完毕！
echo ==============================================================================
echo.
pause
endlocal
exit /b 0
