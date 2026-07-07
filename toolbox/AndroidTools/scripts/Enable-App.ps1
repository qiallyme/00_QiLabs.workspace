[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Package,

    [string] $Serial
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial
Invoke-AndroidAdb -Arguments ($target + @('shell', 'pm', 'enable', $Package)) | Out-Host
Write-Host "Enabled package: $Package"
