# collect_qispark_review.ps1
# Combines the requested QiSpark files into one text file
# and copies the result to the Windows clipboard.

$ErrorActionPreference = "Stop"

$QiLabsRoot = "C:\QiLabs"

if (-not (Test-Path -LiteralPath $QiLabsRoot -PathType Container)) {
    throw "QiLabs root not found: $QiLabsRoot"
}

$files = @(
    "10_QiSpark\build_site.py",
    "10_QiSpark\00_config\site.config.json",
    "10_QiSpark\00_config\services.registry.json",
    "10_QiSpark\00_config\bookmarks.config.json",
    "00_QiLabs.workspace\_qiconfig\_bookmarks\bookmarks.csv",
    "10_QiSpark\00_config\routes.lock.json",
    "10_QiSpark\00_config\publish.filters.json",
    "10_QiSpark\10_site\rules.bookmarks.md",
    "10_QiSpark\10_site\rules.public_publish.md",
    "10_QiSpark\10_site\why.qispark.md"
)

$outputPath = Join-Path $QiLabsRoot "qispark_review_bundle.txt"
$builder = New-Object System.Text.StringBuilder
$missingFiles = New-Object System.Collections.Generic.List[string]

[void]$builder.AppendLine("QISPARK REVIEW BUNDLE")
[void]$builder.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$builder.AppendLine("QiLabs root: $QiLabsRoot")
[void]$builder.AppendLine("Files requested: $($files.Count)")
[void]$builder.AppendLine("")

foreach ($relativePath in $files) {
    $fullPath = Join-Path $QiLabsRoot $relativePath

    [void]$builder.AppendLine("")
    [void]$builder.AppendLine(("=" * 80))
    [void]$builder.AppendLine("FILE: $relativePath")
    [void]$builder.AppendLine(("=" * 80))
    [void]$builder.AppendLine("")

    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
        try {
            $content = [System.IO.File]::ReadAllText($fullPath)

            if ([string]::IsNullOrWhiteSpace($content)) {
                [void]$builder.AppendLine("[FILE IS EMPTY]")
            }
            else {
                [void]$builder.AppendLine($content.TrimEnd())
            }
        }
        catch {
            $errorMessage = $_.Exception.Message
            [void]$builder.AppendLine("[ERROR READING FILE: $errorMessage]")
            $missingFiles.Add("$relativePath - read error")
        }
    }
    else {
        [void]$builder.AppendLine("[FILE NOT FOUND]")
        $missingFiles.Add($relativePath)
    }
}

if ($missingFiles.Count -gt 0) {
    [void]$builder.AppendLine("")
    [void]$builder.AppendLine(("=" * 80))
    [void]$builder.AppendLine("MISSING OR UNREADABLE FILES")
    [void]$builder.AppendLine(("=" * 80))
    [void]$builder.AppendLine("")

    foreach ($missingFile in $missingFiles) {
        [void]$builder.AppendLine($missingFile)
    }
}

$bundle = $builder.ToString()
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

[System.IO.File]::WriteAllText(
    $outputPath,
    $bundle,
    $utf8NoBom
)

Set-Clipboard -Value $bundle

Write-Host ""
Write-Host "QiSpark review bundle created." -ForegroundColor Green
Write-Host "Saved to: $outputPath"
Write-Host "Copied to clipboard: Yes"
Write-Host "Bundle size: $([math]::Round($bundle.Length / 1KB, 1)) KB"

if ($missingFiles.Count -gt 0) {
    Write-Warning "$($missingFiles.Count) file(s) were missing or unreadable."
}