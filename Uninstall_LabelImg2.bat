@echo off
chcp 65001 >nul
title LabelImg2 卸载程序

echo ==================================================================
echo                  LabelImg2 软件卸载程序
echo ==================================================================
echo.
echo 此操作将彻底删除 LabelImg2 的所有程序文件、虚拟环境及桌面快捷方式。
echo.
set /p "CONFIRM=确定要彻底卸载并清理 LabelImg2 吗？(Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo 已取消卸载。
    pause
    exit /b 0
)

echo.
echo [*] 正在删除桌面快捷方式...
del /f /q "%USERPROFILE%\Desktop\LabelImg2.lnk" 2>nul
del /f /q "%PUBLIC%\Desktop\LabelImg2.lnk" 2>nul
powershell -NoProfile -Command "$d = [Environment]::GetFolderPath('Desktop'); $lnk = Join-Path $d 'LabelImg2.lnk'; if (Test-Path $lnk) { Remove-Item -Force $lnk }" 2>nul

echo [*] 正在清理安装目录...
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

set "CLEANER=%TEMP%\labelimg2_cleaner_%RANDOM%.bat"
(
    echo @echo off
    echo timeout /t 2 /nobreak ^>nul
    echo if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
    echo del "%%~f0"
) > "%CLEANER%"

start "" cmd.exe /c "%CLEANER%"

echo [OK] 卸载指令已执行，正在彻底清理文件...
timeout /t 2 >nul
exit /b 0
