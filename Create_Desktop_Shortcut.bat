@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"

set "TARGET_BAT=%SCRIPT_DIR%\Start_LabelImg2.bat"
if exist "%SCRIPT_DIR%\img\app.ico" (
    set "ICON_FILE=%SCRIPT_DIR%\img\app.ico"
) else (
    set "ICON_FILE=%SCRIPT_DIR%\img\labelImg2.ico"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $dirs = @([Environment]::GetFolderPath('Desktop'), \"$env:USERPROFILE\Desktop\", \"$env:USERPROFILE\OneDrive\Desktop\"); foreach ($d in $dirs) { if ($d -and (Test-Path $d)) { try { $s = $ws.CreateShortcut((Join-Path $d 'LabelImg2.lnk')); $s.TargetPath = $env:TARGET_BAT; $s.WorkingDirectory = $env:SCRIPT_DIR; $s.IconLocation = $env:ICON_FILE + ',0'; $s.Description = 'LabelImg2'; $s.Save(); } catch {} } }; $sm = [Environment]::GetFolderPath('Programs'); if ($sm -and (Test-Path $sm)) { try { $s2 = $ws.CreateShortcut((Join-Path $sm 'LabelImg2.lnk')); $s2.TargetPath = $env:TARGET_BAT; $s2.WorkingDirectory = $env:SCRIPT_DIR; $s2.IconLocation = $env:ICON_FILE + ',0'; $s2.Description = 'LabelImg2'; $s2.Save(); } catch {} }"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Shortcuts created successfully on Desktop and Start Menu!
) else (
    echo [ERROR] Failed to create shortcuts.
)

endlocal
exit /b 0
