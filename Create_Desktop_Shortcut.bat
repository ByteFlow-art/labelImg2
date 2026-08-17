@echo off
setlocal
cd /d "%~dp0"

echo [*] Creating Desktop Shortcut for LabelImg2 with App Icon...

set "TARGET_BAT=%~dp0Start_LabelImg2.bat"
if exist "%~dp0img\app.ico" (
    set "ICON_FILE=%~dp0img\app.ico"
) else (
    set "ICON_FILE=%~dp0img\labelImg2.ico"
)


powershell -NoProfile -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; " ^
    "$Desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$Shortcut = $WshShell.CreateShortcut($Desktop + '\LabelImg2.lnk'); " ^
    "$Shortcut.TargetPath = '%TARGET_BAT%'; " ^
    "$Shortcut.WorkingDirectory = '%~dp0'; " ^
    "$Shortcut.IconLocation = '%ICON_FILE%,0'; " ^
    "$Shortcut.Description = 'LabelImg2 Next-Gen - AI Workstation'; " ^
    "$Shortcut.Save();"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Desktop Shortcut created successfully!
    echo You can now double click the [LabelImg2] icon on your Desktop.
) else (
    echo [FAILED] Failed to create desktop shortcut.
)

echo.
pause
endlocal
exit /b 0
