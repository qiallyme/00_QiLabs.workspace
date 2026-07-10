param(
  [Parameter(Mandatory=$true)]
  [string]$Repo
)

$ErrorActionPreference = "Stop"

Write-Host "Checking GitHub CLI auth..." -ForegroundColor Cyan
gh auth status | Out-Host

$Root = Split-Path -Parent $PSScriptRoot
$IssuesDir = Join-Path $Root "issues"

$Issues = @(
  @{
    File = "001_qifinance_audit.md"
    Title = "[QiFinance] Audit current app, schema, imports, and persistence"
    Labels = "app:QiFinance,priority:P1,mode:audit,risk:medium,status:ready-for-codex,data:finance,data:supabase"
  },
  @{
    File = "002_qifinance_phase1_ingestion_review_queue.md"
    Title = "[QiFinance] Design Phase 1 transaction ingestion and review queue"
    Labels = "app:QiFinance,priority:P1,mode:architecture,risk:high,status:ready-for-codex,data:finance,data:tax,data:migration,data:supabase"
  },
  @{
    File = "003_qitarot_persistence.md"
    Title = "[QiTarot] Trace and fix readings not saving to Supabase"
    Labels = "app:QiTarot,priority:P1,mode:patch,risk:medium,status:ready-for-codex,data:supabase,data:rls"
  },
  @{
    File = "004_qitarot_ui_polish.md"
    Title = "[QiTarot] UI polish pass for carousel, centering, mobile hierarchy"
    Labels = "app:QiTarot,priority:P2,mode:ui-polish,risk:medium,status:ready-for-codex"
  },
  @{
    File = "005_qilife_smoke_test.md"
    Title = "[QiLife] Smoke test current revamped app"
    Labels = "app:QiLife,priority:P1,mode:test,risk:medium,status:ready-for-codex,data:supabase"
  }
)

foreach ($Issue in $Issues) {
  $BodyPath = Join-Path $IssuesDir $Issue.File
  if (!(Test-Path $BodyPath)) {
    throw "Missing issue body: $BodyPath"
  }

  Write-Host "Creating issue: $($Issue.Title)" -ForegroundColor Green

  gh issue create `
    --repo $Repo `
    --title $Issue.Title `
    --body-file $BodyPath `
    --label $Issue.Labels
}

Write-Host "Done. Issues created in $Repo." -ForegroundColor Cyan
