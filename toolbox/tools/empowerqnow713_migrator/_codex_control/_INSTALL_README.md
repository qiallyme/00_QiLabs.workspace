# QiCodex Control Drop-In Install

## What this zip does

This is a drop-in overlay for the QiLabs workspace.

It adds:

- Codex control docs to `60_QiApps/67_QiCodex/`
- issue templates and seed issues to `60_QiApps/67_QiCodex/issues/`
- a GitHub issue creation helper to `60_QiApps/67_QiCodex/scripts/`
- a vault summary to `40_QiVault/13_system/`

It does **not** modify existing files.

## Where to unzip

Unzip this at the folder that contains these folders:

- `00_QiLabs.workspace`
- `10_QiSpark`
- `20_QiServer`
- `40_QiVault`
- `60_QiApps`

That folder is your QiLabs root.

Do **not** unzip inside `60_QiApps/67_QiCodex/`.
Do **not** unzip inside `00_QiLabs.workspace/`.

## Windows PowerShell

From wherever you downloaded the zip:

```powershell
Expand-Archive -Path .\QiCodex_Control_DropIn.zip -DestinationPath "C:\PATH\TO\QiLabs" -Force
```

Replace `C:\PATH\TO\QiLabs` with the actual path to your QiLabs root.

## Expected new files

```text
40_QiVault/
  13_system/
    codex_agent_workflow.md

60_QiApps/
  67_QiCodex/
    QI_CODEX_CONTROL_CENTER.md
    WORK_ORDER_TEMPLATE.md
    ISSUE_LABELS.md
    APP_PRIORITIES.md
    VAULT_SYNC_TEMPLATE.md
    CODEX_FIRST_PROMPT.md
    issues/
      README.md
      001_qifinance_audit.md
      002_qifinance_phase1_ingestion_review_queue.md
      003_qitarot_persistence.md
      004_qitarot_ui_polish.md
      005_qilife_smoke_test.md
    scripts/
      create_github_issues.ps1
```

## After unzipping

Open:

```text
60_QiApps/67_QiCodex/CODEX_FIRST_PROMPT.md
```

Paste that into local Codex from the QiLabs root.

## Optional: create GitHub issues

If GitHub CLI is installed and authenticated:

```powershell
gh auth status
.\60_QiApps\67_QiCodex\scripts\create_github_issues.ps1 -Repo "OWNER/REPO"
```

Example:

```powershell
.\60_QiApps\67_QiCodex\scripts\create_github_issues.ps1 -Repo "qiallyme/20_QiServer"
```

Only run the example if that is actually the repo you want issues created in.
