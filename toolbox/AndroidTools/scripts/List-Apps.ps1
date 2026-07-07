[CmdletBinding()]
param(
    [string] $Serial,
    [switch] $ThirdParty,
    [switch] $System,
    [switch] $Disabled,
    [switch] $Enabled,
    [string] $Search
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\lib\AndroidTools.ps1')

$target = Get-AndroidAdbTargetArgs -Serial $Serial
$pmArgs = @('shell', 'pm', 'list', 'packages', '-f', '-i', '-U')

if ($ThirdParty) { $pmArgs += '-3' }
if ($System) { $pmArgs += '-s' }
if ($Disabled) { $pmArgs += '-d' }
if ($Enabled) { $pmArgs += '-e' }

$lines = Invoke-AndroidAdb -Arguments ($target + $pmArgs)

$apps = foreach ($line in $lines) {
    $text = $line.ToString().Trim()
    if ($text -notmatch '^package:(?<Path>.+?)=(?<Package>[^\s]+)(?:\s+installer=(?<Installer>[^\s]+))?(?:\s+uid:(?<Uid>\d+))?') {
        continue
    }

    $installer = ''
    if ($Matches.ContainsKey('Installer')) {
        $installer = $Matches['Installer']
    }

    $uid = ''
    if ($Matches.ContainsKey('Uid')) {
        $uid = $Matches['Uid']
    }

    [pscustomobject]@{
        Package = $Matches.Package
        Installer = $installer
        Uid = $uid
        Path = $Matches.Path
    }
}

if ($Search) {
    $apps = @($apps | Where-Object {
        $_.Package -like "*$Search*" -or
        $_.Installer -like "*$Search*" -or
        $_.Path -like "*$Search*"
    })
}

$apps | Sort-Object Package | Format-Table Package, Installer, Uid, Path -AutoSize
