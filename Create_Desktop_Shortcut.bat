@echo off
setlocal
cd /d "%~dp0"

set "TARGET_BAT=%~dp0Start_LabelImg2.bat"
if exist "%~dp0img\app.ico" (
    set "ICON_FILE=%~dp0img\app.ico"
) else (
    set "ICON_FILE=%~dp0img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut($d + '\LabelImg2.lnk'); $s.TargetPath = 'C:\Windows\System32\cmd.exe'; $s.Arguments = '/c start \"\" \"' + $env:TARGET_BAT + '\"'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = $env:ICON_FILE + ',0'; $s.Description = 'LabelImg2'; $s.WindowStyle = 7; $s.Save();"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Desktop Shortcut created successfully!
) else (
    echo [ERROR] Failed to create desktop shortcut.
)

endlocal
exit /b 0
