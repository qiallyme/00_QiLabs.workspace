@echo off
setlocal
set SCRIPT_DIR=%~dp0
powershell -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%scripts\create_github_issues.ps1"
pause
