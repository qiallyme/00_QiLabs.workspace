$ErrorActionPreference = "Stop"

$toolboxRoot = "C:\QiLabs\00_QiLabs.workspace\toolbox"
$exe = Join-Path $toolboxRoot "QiLabsToolbox.exe"
$fallbackBat = Join-Path $toolboxRoot "launch_dynamic_toolbox.bat"
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "QiLabs Toolbox.lnk"

if (Test-Path $exe) {
  $target = $exe
  $args = ""
} elseif (Test-Path $fallbackBat) {
  $target = "$env:WINDIR\System32\cmd.exe"
  $args = "/c `"$fallbackBat`""
} else {
  throw "Could not find QiLabsToolbox.exe or launch_dynamic_toolbox.bat under $toolboxRoot"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = $args
$shortcut.WorkingDirectory = $toolboxRoot
$shortcut.Description = "Launch QiLabs Toolbox at sign-in"
$shortcut.Save()

Write-Host "Autostart installed:" $shortcutPath
Write-Host "Target:" $target
