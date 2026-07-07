[CmdletBinding()]
param(
    [string] $Serial,
    [switch] $IncludeFullPackageDump
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial
$dir = New-AndroidReportDirectory -Prefix 'device-state'

Save-AndroidAdbOutput -Path (Join-Path $dir 'adb-devices.txt') -Arguments @('devices', '-l')
Save-AndroidAdbOutput -Path (Join-Path $dir 'getprop.txt') -Arguments ($target + @('shell', 'getprop'))
Save-AndroidAdbOutput -Path (Join-Path $dir 'users.txt') -Arguments ($target + @('shell', 'pm', 'list', 'users')) -AllowFailure
Save-AndroidAdbOutput -Path (Join-Path $dir 'packages-all.txt') -Arguments ($target + @('shell', 'pm', 'list', 'packages', '-f', '-i', '-U'))
Save-AndroidAdbOutput -Path (Join-Path $dir 'packages-third-party.txt') -Arguments ($target + @('shell', 'pm', 'list', 'packages', '-3', '-f', '-i', '-U'))
Save-AndroidAdbOutput -Path (Join-Path $dir 'packages-disabled.txt') -Arguments ($target + @('shell', 'pm', 'list', 'packages', '-d', '-f', '-i', '-U')) -AllowFailure
Save-AndroidAdbOutput -Path (Join-Path $dir 'device-policy.txt') -Arguments ($target + @('shell', 'dumpsys', 'device_policy')) -AllowFailure

if ($IncludeFullPackageDump) {
    Save-AndroidAdbOutput -Path (Join-Path $dir 'dumpsys-package.txt') -Arguments ($target + @('shell', 'dumpsys', 'package')) -AllowFailure
}

Write-Host "Device report saved to:"
Write-Host $dir
