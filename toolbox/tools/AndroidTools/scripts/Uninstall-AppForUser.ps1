[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Package,

    [string] $Serial,
    [switch] $KeepData,
    [switch] $Yes
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial

Write-Host "Package path:"
Invoke-AndroidAdb -Arguments ($target + @('shell', 'pm', 'path', $Package)) -AllowFailure | Out-Host

if (-not (Confirm-AndroidPackageAction -Package $Package -Action 'uninstall for Android user 0' -Yes:$Yes)) {
    Write-Host "Cancelled."
    exit 0
}

$uninstallArgs = @('shell', 'pm', 'uninstall')
if ($KeepData) {
    $uninstallArgs += '-k'
}
$uninstallArgs += @('--user', '0', $Package)

Invoke-AndroidAdb -Arguments ($target + $uninstallArgs) | Out-Host
Write-Host "Done. If this was a built-in package, try restoring with:"
Write-Host ".\scripts\Install-Existing-App.ps1 -Package $Package"
