[CmdletBinding()]
param(
    [string] $Serial,
    [switch] $NoAudio,
    [switch] $TurnScreenOff
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$platformTools = Join-Path $root 'tools\platform-tools'
$scrcpyDir = Join-Path $root 'tools\scrcpy'
$scrcpy = Join-Path $scrcpyDir 'scrcpy.exe'

if (-not (Test-Path -LiteralPath $scrcpy)) {
    throw "scrcpy.exe was not found at $scrcpy."
}

if (($env:Path -split ';') -notcontains $platformTools) {
    $env:Path = "$platformTools;$env:Path"
}

if (($env:Path -split ';') -notcontains $scrcpyDir) {
    $env:Path = "$scrcpyDir;$env:Path"
}

$scrcpyArgs = @()
if ($Serial) {
    $scrcpyArgs += @('--serial', $Serial)
}
if ($NoAudio) {
    $scrcpyArgs += '--no-audio'
}
if ($TurnScreenOff) {
    $scrcpyArgs += '--turn-screen-off'
}

& $scrcpy @scrcpyArgs
