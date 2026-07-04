@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 data_extractor.py
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python data_extractor.py
  exit /b %errorlevel%
)
echo Python was not found. Install Python or add it to PATH.
pause
exit /b 1
