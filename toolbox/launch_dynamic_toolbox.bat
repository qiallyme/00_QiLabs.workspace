@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0QiLabsToolbox.exe" (
  start "" "%~dp0QiLabsToolbox.exe"
) else (
  py "%~dp0main_ui.py"
)
