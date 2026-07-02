<#
cleanup_toolbox_folder.ps1
Safe cleanup for C:\QiLabs\00_QiLabs.workspace\toolbox

Default mode is DRY RUN. Nothing moves/deletes unless you pass -Apply.
This script archives clutter into _archive\cleanup-YYYYMMDD-HHMMSS so you can test the toolbox before deleting anything.
#>

param(
    [switch]$Apply,
    [switch]$StopToolboxProcesses,
    [switch]$KeepReviewBundles
)

$ErrorActionPreference = "Stop"

$Root = "C:\QiLabs\00_QiLabs.workspace\toolbox"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ArchiveRoot = Join-Path $Root "_archive\cleanup-$Stamp"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Dry($Message) {
    if ($Apply) {
        Write-Host "    $Message" -ForegroundColor Green
    } else {
        Write-Host "    [DRY RUN] $Message" -ForegroundColor Yellow
    }
}

function Ensure-Dir($Path) {
    if ($Apply -and -not (Test-Path $Path)) {
        New-Item -ItemType Directory -Force $Path | Out-Null
    }
}

function Get-RelativePath($Path) {
    $full = (Resolve-Path $Path).Path
    return $full.Replace($Root, "").TrimStart("\")
}

function Move-ToArchive($Path, $Bucket = "misc") {
    if (-not (Test-Path $Path)) { return }
    $resolved = (Resolve-Path $Path).Path
    $rel = $resolved.Replace($Root, "").TrimStart("\")
    $dest = Join-Path (Join-Path $ArchiveRoot $Bucket) $rel
    $destParent = Split-Path $dest -Parent

    Write-Dry "Archive: $rel -> _archive\cleanup-$Stamp\$Bucket\$rel"

    if ($Apply) {
        Ensure-Dir $destParent
        Move-Item -LiteralPath $resolved -Destination $dest -Force
    }
}

function Remove-Generated($Path, $Bucket = "generated_build_outputs") {
    if (-not (Test-Path $Path)) { return }
    Move-ToArchive $Path $Bucket
}

function Clear-HousekeepingRuntimeFolder($FolderName) {
    $folder = Join-Path $Root "_housekeeping\$FolderName"
    if (-not (Test-Path $folder)) { return }

    Get-ChildItem $folder -Force | Where-Object { $_.Name -ne ".gitkeep" } | ForEach-Object {
        Move-ToArchive $_.FullName "housekeeping_runtime"
    }

    $gitkeep = Join-Path $folder ".gitkeep"
    if ($Apply -and -not (Test-Path $gitkeep)) {
        New-Item -ItemType File -Force $gitkeep | Out-Null
    }
}

function Stop-ToolboxProcessesSafe {
    Write-Step "Stopping old toolbox processes"

    $names = @("QiLabsToolbox", "QiOne_Tools", "destroyer")
    foreach ($name in $names) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Dry "Stop process: $($_.ProcessName).exe PID $($_.Id)"
            if ($Apply) { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
        }
    }

    $escapedRoot = [Regex]::Escape($Root)
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^(python|pythonw|py)\.exe$" -and
        $_.CommandLine -match $escapedRoot -and
        ($_.CommandLine -match "main_ui\.py|toolbox_dynamic_ui\.py|QiLabsToolbox|housekeeping_ui\.py")
    } | ForEach-Object {
        Write-Dry "Stop toolbox Python process PID $($_.ProcessId): $($_.CommandLine)"
        if ($Apply) { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
}

Set-Location $Root

Write-Host "QiLabs Toolbox Cleanup" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Mode: $(if ($Apply) { 'APPLY' } else { 'DRY RUN' })"
Write-Host "Archive: $ArchiveRoot"

if ($StopToolboxProcesses) {
    Stop-ToolboxProcessesSafe
}

Write-Step "Archive generated build outputs"
Remove-Generated (Join-Path $Root "build")
Remove-Generated (Join-Path $Root "dist")
Remove-Generated (Join-Path $Root "QiLabsToolbox.spec")

Write-Step "Archive patch leftovers and review bundles"
Move-ToArchive (Join-Path $Root "_patch_backups") "patch_leftovers"
Move-ToArchive (Join-Path $Root "_legacy_static_builder") "legacy"
Move-ToArchive (Join-Path $Root "extracted_toolbox") "review_leftovers"
if (-not $KeepReviewBundles) {
    Move-ToArchive (Join-Path $Root "_review_bundles_for_chatgpt") "review_leftovers"
}

$patchFiles = @(
    "README_DYNAMIC_TOOLBOX_V0_2.md",
    "README_DYNAMIC_TOOLBOX_V0_4_CLASSIC_COMPAT.md",
    "README_QIACCESS_BOOKMARKS_TOOL.md",
    "README_QILABS_TOOLBOX_V0_5_PATCH.md",
    "README_QILABS_TOOLBOX_V0_6.md",
    "install_v0_6_housekeeping_scroll_fix.ps1",
    "make_toolbox_review_bundles.ps1",
    "toolbox_dynamic_ui.py",
    "toolbox_autofix_report.json"
)
foreach ($file in $patchFiles) {
    Move-ToArchive (Join-Path $Root $file) "patch_leftovers"
}

Write-Step "Archive housekeeping runtime state, keeping housekeeping app code"
foreach ($folder in @("backups", "logs", "manifests", "plans", "reports", "summaries")) {
    Clear-HousekeepingRuntimeFolder $folder
}

Write-Step "Archive pending/salvage tools and loose root scripts inside tools"
Move-ToArchive (Join-Path $Root "tools\_pending") "tools_pending"

# Any files directly under tools\ are loose scripts, not valid active plugin folders.
Get-ChildItem (Join-Path $Root "tools") -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Move-ToArchive $_.FullName "tools_loose_files"
}

Write-Step "Keep active source in place"
$keep = @(
    "QiLabsToolbox.exe",
    "README.md",
    "TOOLBOX_ARCHITECTURE_NOTES.md",
    "build_qione_dynamic.bat",
    "build_toolbox_runtime.ps1",
    "file_version_info.txt",
    "install_qilabs_toolbox_autostart.bat",
    "launch_dynamic_toolbox.bat",
    "main_ui.py",
    "remove_qilabs_toolbox_autostart.bat",
    "requirements.txt",
    "toolbox_autofix_manifest_issues.py",
    "toolbox_manifest.schema.json",
    "toolbox_registry.config.json",
    "toolbox_registry.json",
    "toolbox_validation_report.md",
    "core",
    "examples",
    "scripts",
    "toolbox_core",
    "tools",
    "_housekeeping"
)
$keep | ForEach-Object { Write-Host "    KEEP: $_" -ForegroundColor DarkGray }

Write-Step "Create archive note"
$note = @"
QiLabs Toolbox Cleanup Archive
Created: $(Get-Date)
Root: $Root
Mode: $(if ($Apply) { 'APPLY' } else { 'DRY RUN' })

This archive contains generated outputs, patch leftovers, old legacy builder files,
review bundles, housekeeping runtime payloads, pending tools, and loose root scripts.

After QiLabsToolbox.exe opens and plugins work, you can delete this archive folder:
$ArchiveRoot
"@
if ($Apply) {
    Ensure-Dir $ArchiveRoot
    Set-Content -Path (Join-Path $ArchiveRoot "README_CLEANUP_ARCHIVE.txt") -Value $note -Encoding UTF8
}

Write-Step "Done"
if ($Apply) {
    Write-Host "Cleanup applied. Archive created at:" -ForegroundColor Green
    Write-Host $ArchiveRoot -ForegroundColor Green
    Write-Host ""
    Write-Host "Now test:" -ForegroundColor Cyan
    Write-Host "  py -m compileall main_ui.py toolbox_core core" -ForegroundColor White
    Write-Host "  .\QiLabsToolbox.exe" -ForegroundColor White
} else {
    Write-Host "Dry run only. Nothing moved." -ForegroundColor Yellow
    Write-Host "To apply:" -ForegroundColor Cyan
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\cleanup_toolbox_folder.ps1 -Apply" -ForegroundColor White
}
