@echo off
chcp 65001 >nul
setlocal

REM ==============================================================================
REM   LabelImg2 - 一键打包生成 Windows 独立可执行程序 (.exe)
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================================
echo            LabelImg2 - PyInstaller 独立桌面程序打包构建工具
echo ==============================================================================
echo.

REM 激活 Conda 环境或本地环境
set "CONDA_ACTIVATE="
for %%P in (
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
    "C:\Miniconda3\Scripts\activate.bat"
    "C:\Anaconda3\Scripts\activate.bat"
) do (
    if not defined CONDA_ACTIVATE if exist "%%~P" set "CONDA_ACTIVATE=%%~P"
)

if defined CONDA_ACTIVATE (
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
)

python "%SCRIPT_DIR%\build_exe.py"

pause
endlocal
exit /b %ERRORLEVEL%
