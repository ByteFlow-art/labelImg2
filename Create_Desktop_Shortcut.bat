@echo off
chcp 65001 >nul
setlocal

REM ==============================================================================
REM   LabelImg2 - 创建桌面快捷方式 (带高清 App 图标)
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "ICON_FILE=%SCRIPT_DIR%img\labelImg2.ico"
set "TARGET_FILE=%SCRIPT_DIR%Start_LabelImg2.bat"

if exist "%SCRIPT_DIR%dist\LabelImg2\LabelImg2.exe" (
    set "TARGET_FILE=%SCRIPT_DIR%dist\LabelImg2\LabelImg2.exe"
)

echo [*] 正在为 LabelImg2 创建桌面快捷方式 (使用专属 App 图标)...

powershell -NoProfile -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; " ^
    "$Desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$Shortcut = $WshShell.CreateShortcut($Desktop + '\LabelImg2.lnk'); " ^
    "$Shortcut.TargetPath = '%TARGET_FILE%'; " ^
    "$Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; " ^
    "$Shortcut.IconLocation = '%ICON_FILE%,0'; " ^
    "$Shortcut.Description = 'LabelImg2 Next-Gen - AI 智能计算机视觉标注工作台'; " ^
    "$Shortcut.Save();"

if errorlevel 0 (
    echo [OK] 桌面快捷方式创建成功！您可以在桌面上直接双击 [LabelImg2] 图标启动软件。
) else (
    echo [提示] 快捷方式创建失败，请手动将 Start_LabelImg2.bat 发送到桌面。
)

echo.
pause
endlocal
exit /b 0
