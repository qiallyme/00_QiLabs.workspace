@echo off
setlocal
cd /d "%~dp0"
echo Building QiLabs Toolbox dynamic plugin host...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_toolbox_runtime.ps1"
echo.
pause
