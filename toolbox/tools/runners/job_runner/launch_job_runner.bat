@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 job_runner.py
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python job_runner.py
  exit /b %errorlevel%
)
echo Python was not found. Install Python or add it to PATH.
pause
exit /b 1
