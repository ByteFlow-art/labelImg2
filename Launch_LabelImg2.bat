@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
call "%SCRIPT_DIR%\Start_LabelImg2.bat" %*
endlocal

