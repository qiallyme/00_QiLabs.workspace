# QiLabs Codex Issue Seeds

These are starter GitHub issue bodies for the first controlled Codex work queue.

Recommended first five issues:

1. `[QiFinance] Audit current app, schema, imports, and persistence`
2. `[QiFinance] Design Phase 1 transaction ingestion and review queue`
3. `[QiTarot] Trace and fix readings not saving to Supabase`
4. `[QiTarot] UI polish pass for carousel, centering, mobile hierarchy`
5. `[QiLife] Smoke test current revamped app`

Use these manually, or run the included PowerShell helper:

```powershell
.\60_QiApps\67_QiCodex\scripts\create_github_issues.ps1 -Repo "OWNER/REPO"
```

Requires GitHub CLI:

```powershell
gh auth status
```

If `gh auth status` fails, log in first:

```powershell
gh auth login
```
