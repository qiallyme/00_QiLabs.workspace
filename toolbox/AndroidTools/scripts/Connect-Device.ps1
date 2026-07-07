[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$adb = Get-AndroidAdbPath
Write-Host "Starting ADB server..."
& $adb start-server | Out-Host

Write-Host ""
Write-Host "Connected devices:"
& $adb devices -l | Out-Host

Write-Host ""
Write-Host "Expected state is: device"
Write-Host "If you see unauthorized, unlock the phone and accept the USB debugging prompt."
Write-Host "If you see nothing, try another USB cable/port and make sure the cable supports data."
