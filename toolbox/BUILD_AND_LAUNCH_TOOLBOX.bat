@echo off
setlocal EnabledDelayedExpansion
cd /d "%~dp0"
title QiLabs Toolbox Maintenance Kit

:menu
cls
echo ======================================================================
echo                      QiLabs Toolbox Interactive Builder
echo ======================================================================
echo.
echo   [1] Build dynamic plugin host (QiLabsToolbox.exe)
echo   [2] Refresh plugin registry and manifests
echo   [3] Run plugin validation check and show report
echo   [4] Rebuild AndroidTools launcher binary
echo   [5] Launch QiLabs Toolbox (GUI / Script)
echo   [6] Clean build and cache files (build/, dist/, spec)
echo   [7] Exit
echo.
echo ======================================================================
set /p opt="Select an option [1-7]: "

if "%opt%"=="1" goto build_exe
if "%opt%"=="2" goto refresh_reg
if "%opt%"=="3" goto validate_plugins
if "%opt%"=="4" goto build_android
if "%opt%"=="5" goto launch_toolbox
if "%opt%"=="6" goto clean_temp
if "%opt%"=="7" goto end
goto menu

:build_exe
echo.
echo [INFO] Running PyInstaller build...
powershell -NoProfile -ExecutionPolicy Bypass -File build_toolbox_runtime.ps1
echo.
pause
goto menu

:refresh_reg
echo.
echo [INFO] Rebuilding plugin registry...
py -m toolbox_core.plugin_registry .
echo.
pause
goto menu

:validate_plugins
echo.
echo [INFO] Running registry refresh and checking validation report...
py -m toolbox_core.plugin_registry .
if exist "toolbox_validation_report.md" (
  type "toolbox_validation_report.md"
) else (
  echo [ERROR] No validation report found.
)
echo.
pause
goto menu

:build_android
echo.
echo [INFO] Compiling AndroidTools launcher...
if exist "tools\AndroidTools\Build-AndroidToolsLauncher.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "tools\AndroidTools\Build-AndroidToolsLauncher.ps1"
) else (
  echo [ERROR] Could not find Build-AndroidToolsLauncher.ps1 in tools\AndroidTools\
)
echo.
pause
goto menu

:launch_toolbox
echo.
echo [INFO] Launching QiLabs Toolbox...
if exist "QiLabsToolbox.exe" (
  start "" "QiLabsToolbox.exe"
) else (
  py "main_ui.py"
)
exit /b

:clean_temp
echo.
echo [INFO] Cleaning temp files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "QiLabsToolbox.spec" del /f /q "QiLabsToolbox.spec"
echo Clean complete.
echo.
pause
goto menu

:end
endlocal
