@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\remove_qilabs_toolbox_autostart.ps1"
pause
