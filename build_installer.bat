@echo off
chcp 65001 >nul
setlocal

REM ==============================================================================
REM   LabelImg2 - 一键构建官方安装程序 (LabelImg2_Setup_v1.0.0.exe)
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================================
echo            LabelImg2 - 官方独立安装程序打包构建工具 (Setup Builder)
echo ==============================================================================
echo.

set "CONDA_ACTIVATE="
for %%P in (
    "C:\D\Conda\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    "C:\ProgramData\miniconda3\Scripts\activate.bat"
    "C:\Miniconda3\Scripts\activate.bat"
    "C:\Anaconda3\Scripts\activate.bat"
) do (
    if not defined CONDA_ACTIVATE if exist "%%~P" set "CONDA_ACTIVATE=%%~P"
)

if defined CONDA_ACTIVATE (
    call "!CONDA_ACTIVATE!" labelimg2 >nul 2>&1
)

python "%SCRIPT_DIR%\build_installer.py"

pause
endlocal
exit /b %ERRORLEVEL%
