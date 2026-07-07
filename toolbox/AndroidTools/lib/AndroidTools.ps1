Set-StrictMode -Version 2.0

$script:AndroidToolsRoot = Split-Path -Parent $PSScriptRoot

function Get-AndroidToolsRoot {
    return $script:AndroidToolsRoot
}

function Get-AndroidAdbPath {
    $root = Get-AndroidToolsRoot
    $localAdb = Join-Path $root 'tools\platform-tools\adb.exe'

    if (Test-Path -LiteralPath $localAdb) {
        return $localAdb
    }

    $pathAdb = Get-Command adb -ErrorAction SilentlyContinue
    if ($pathAdb) {
        return $pathAdb.Source
    }

    throw "adb.exe was not found. Run the toolkit installer or download Android SDK Platform Tools."
}

function Invoke-AndroidAdb {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments,

        [switch] $AllowFailure
    )

    $adb = Get-AndroidAdbPath
    $previousErrorActionPreference = $ErrorActionPreference

    try {
        $ErrorActionPreference = 'Continue'
        $output = & $adb @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        $joined = $Arguments -join ' '
        $message = ($output | Out-String).Trim()
        throw "ADB command failed ($joined). Exit code: $exitCode. Output: $message"
    }

    return $output
}

function Get-AndroidAdbTargetArgs {
    param(
        [string] $Serial
    )

    if ($Serial) {
        return @('-s', $Serial)
    }

    $rows = @(Invoke-AndroidAdb -Arguments @('devices') | Select-Object -Skip 1 | Where-Object { $_.ToString().Trim() -ne '' })
    $devices = @(
        foreach ($row in $rows) {
            if ($row -match '^(\S+)\s+(\S+)') {
                [pscustomobject]@{
                    Serial = $Matches[1]
                    State = $Matches[2]
                    Raw = $row
                }
            }
        }
    )

    if ($devices.Count -eq 0) {
        throw "No Android device was detected. Check the USB cable, USB mode, drivers, and USB debugging prompt."
    }

    $ready = @($devices | Where-Object { $_.State -eq 'device' })
    if ($ready.Count -eq 1) {
        return @('-s', $ready[0].Serial)
    }

    if ($ready.Count -gt 1) {
        $serials = ($ready | ForEach-Object { $_.Serial }) -join ', '
        throw "Multiple authorized devices are connected: $serials. Re-run with -Serial <device-serial>."
    }

    $unauthorized = @($devices | Where-Object { $_.State -eq 'unauthorized' })
    if ($unauthorized.Count -gt 0) {
        throw "The device is connected but unauthorized. Unlock the phone and accept the USB debugging RSA prompt."
    }

    $states = ($devices | ForEach-Object { "$($_.Serial):$($_.State)" }) -join ', '
    throw "No authorized device is ready. Current ADB states: $states"
}

function Confirm-AndroidPackageAction {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Package,

        [Parameter(Mandatory = $true)]
        [string] $Action,

        [switch] $Yes
    )

    if ($Yes) {
        return $true
    }

    Write-Host ""
    Write-Host "About to $Action package: $Package"
    Write-Host "Type the exact package name to confirm, or press Enter to cancel."
    $answer = Read-Host 'Confirm package'

    return ($answer -eq $Package)
}

function New-AndroidReportDirectory {
    param(
        [string] $Prefix = 'device-state'
    )

    $root = Get-AndroidToolsRoot
    $reports = Join-Path $root 'reports'
    New-Item -ItemType Directory -Force -Path $reports | Out-Null

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dir = Join-Path $reports "$Prefix-$stamp"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    return $dir
}

function Save-AndroidAdbOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments,

        [switch] $AllowFailure
    )

    $output = Invoke-AndroidAdb -Arguments $Arguments -AllowFailure:$AllowFailure
    $output | Set-Content -LiteralPath $Path -Encoding UTF8
}
