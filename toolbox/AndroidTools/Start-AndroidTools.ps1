[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PlatformTools = Join-Path $Root 'tools\platform-tools'
$ScrcpyTools = Join-Path $Root 'tools\scrcpy'
$Adb = Join-Path $PlatformTools 'adb.exe'

if (-not (Test-Path -LiteralPath $Adb)) {
    throw "ADB was not found at $Adb. Reinstall platform-tools before using this toolkit."
}

if (($env:Path -split ';') -notcontains $PlatformTools) {
    $env:Path = "$PlatformTools;$env:Path"
}

if (Test-Path -LiteralPath (Join-Path $ScrcpyTools 'scrcpy.exe')) {
    if (($env:Path -split ';') -notcontains $ScrcpyTools) {
        $env:Path = "$ScrcpyTools;$env:Path"
    }
}

Write-Host "Android Platform Tools are ready for this PowerShell session."
Write-Host "ADB path: $Adb"
Write-Host ""
& $Adb version
Write-Host ""
Write-Host "Next:"
Write-Host "  .\scripts\Connect-Device.ps1"
Write-Host "  .\scripts\Backup-AndroidState.ps1"
Write-Host "  .\scripts\List-Apps.ps1 -ThirdParty"
Write-Host "  .\scripts\Start-Scrcpy.ps1"
