[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Package,

    [string] $Serial
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial
Invoke-AndroidAdb -Arguments ($target + @('shell', 'cmd', 'package', 'install-existing', '--user', '0', $Package)) | Out-Host
Invoke-AndroidAdb -Arguments ($target + @('shell', 'pm', 'enable', $Package)) -AllowFailure | Out-Host
Write-Host "Requested reinstall/enable for package: $Package"
