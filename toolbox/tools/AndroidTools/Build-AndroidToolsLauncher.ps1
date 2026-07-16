[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$Source = Join-Path $Root 'src\AndroidToolsLauncher\Program.cs'
$Output = Join-Path $Root 'AndroidTools.exe'

if (-not (Test-Path -LiteralPath $Csc)) {
    throw "Could not find the .NET Framework C# compiler at $Csc."
}

& $Csc /nologo /target:winexe /optimize+ /out:$Output /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Management.dll /reference:System.Windows.Forms.dll $Source

if ($LASTEXITCODE -ne 0) {
    throw "Launcher build failed with exit code $LASTEXITCODE."
}

Write-Host "Built $Output"
