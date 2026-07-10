# GitHub CLI diagnostics for QiLabs / EmpowerQNow713
Write-Host "Checking GitHub CLI..." -ForegroundColor Cyan
$paths = @(
  "gh",
  "C:\Program Files\GitHub CLI\gh.exe",
  "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe"
)
$gh = $null
foreach ($p in $paths) {
  try {
    if ($p -eq "gh") {
      $cmd = Get-Command gh -ErrorAction SilentlyContinue
      if ($cmd) { $gh = $cmd.Source; break }
    } elseif (Test-Path $p) { $gh = $p; break }
  } catch {}
}
if (-not $gh) {
  Write-Host "gh.exe not found. Install with: winget install --id GitHub.cli" -ForegroundColor Red
  exit 1
}
Write-Host "Found gh at: $gh" -ForegroundColor Green
& $gh --version
Write-Host "\nAuth status:" -ForegroundColor Cyan
& $gh auth status
Write-Host "\nGit status at current path:" -ForegroundColor Cyan
git status
