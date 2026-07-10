@echo off
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%~dp0interactive_qivault_empower_migrator.pyw"
  exit /b
)

where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw "%~dp0interactive_qivault_empower_migrator.pyw"
  exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
  start "" python "%~dp0interactive_qivault_empower_migrator.pyw"
  exit /b
)

msg * "Python was not found. Install Python, then double-click RUN_INTERACTIVE_MIGRATOR.bat again."
