$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $Root

Write-Host "Building QiLabsToolbox.exe dynamic plugin host..." -ForegroundColor Cyan
Write-Host "Root: $Root" -ForegroundColor DarkCyan

function Stop-ToolboxProcesses {
    Write-Host "Stopping old toolbox processes..." -ForegroundColor Yellow
    $exeNames = @("QiLabsToolbox", "QiOne_Tools")
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $exeNames -contains $_.ProcessName } |
        ForEach-Object {
            Write-Host "  stop $($_.ProcessName) pid=$($_.Id)"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }

    $escapedRoot = [Regex]::Escape($Root)
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.Name -match "^(python|pythonw|py)\.exe$" -and
            $_.CommandLine -match $escapedRoot -and
            ($_.CommandLine -match "main_ui\.py|toolbox_dynamic_ui\.py|toolbox_autofix_manifest_issues\.py|build_toolbox_runtime")
        } |
        ForEach-Object {
            Write-Host "  stop python pid=$($_.ProcessId) $($_.CommandLine)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

Stop-ToolboxProcesses

$py = "py"

try {
    & $py -m pip show pyinstaller *> $null
} catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    & $py -m pip install --upgrade pip
    & $py -m pip install pyinstaller
}

Write-Host "Cleaning build artifacts..." -ForegroundColor Yellow
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }
if (Test-Path ".\QiLabsToolbox.spec") { Remove-Item ".\QiLabsToolbox.spec" -Force }

Write-Host "Refreshing plugin registry..." -ForegroundColor Yellow
& $py -m toolbox_core.plugin_registry "$Root"

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
& $py -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "QiLabsToolbox" `
  --version-file "file_version_info.txt" `
  --collect-submodules "toolbox_core" `
  "main_ui.py"

$built = Join-Path $Root "dist\QiLabsToolbox.exe"
$target = Join-Path $Root "QiLabsToolbox.exe"

if (!(Test-Path $built)) {
    throw "Build finished but $built was not found."
}

Copy-Item $built $target -Force

Write-Host ""
Write-Host "DONE: $target" -ForegroundColor Green
Write-Host "Pin this EXE. Plugins under tools\<category>\<plugin> are discovered at runtime." -ForegroundColor Green
