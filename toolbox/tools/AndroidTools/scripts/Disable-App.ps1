[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Package,

    [string] $Serial,
    [switch] $Yes
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial

Write-Host "Package path:"
Invoke-AndroidAdb -Arguments ($target + @('shell', 'pm', 'path', $Package)) -AllowFailure | Out-Host

if (-not (Confirm-AndroidPackageAction -Package $Package -Action 'disable for Android user 0' -Yes:$Yes)) {
    Write-Host "Cancelled."
    exit 0
}

Invoke-AndroidAdb -Arguments ($target + @('shell', 'pm', 'disable-user', '--user', '0', $Package)) | Out-Host
Write-Host "Done. Re-enable with:"
Write-Host ".\scripts\Enable-App.ps1 -Package $Package"
