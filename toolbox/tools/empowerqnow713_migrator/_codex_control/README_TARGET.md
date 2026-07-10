# EmpowerQNow713 Migrator — Codex Control Drop-In

This folder holds the local Codex control docs, GitHub issue templates, and scripts for the EmpowerQNow713 migrator lane.

## Where this belongs

Expected Windows path:

```text
C:\QiLabs\00_QiLabs.workspace\toolbox\tools\empowerqnow713_migrator\_codex_control
```

Unzip the package at the QiLabs root:

```powershell
Expand-Archive -Path .\EmpowerQNow713_Codex_Control_DropIn.zip -DestinationPath "C:\QiLabs" -Force
```

Do **not** unzip inside the `empowerqnow713_migrator` folder unless you manually strip the archive paths.

## What to open first

Open:

```text
_codex_control/CODEX_FIRST_PROMPT.md
```

Paste that prompt into local Codex while your terminal is pointed at the relevant repo or workspace.

## GitHub Issues

Issue templates are in:

```text
_codex_control/issues/
```

The issue creation script is:

```text
_codex_control/scripts/create_github_issues.ps1
```

If `gh` is not recognized after installation, use the full executable path or fix PATH first.
Common GitHub CLI install path:

```text
C:\Program Files\GitHub CLI\gh.exe
```

## Safe operating rule

Codex should inspect first, explain second, patch third, test fourth, and document fifth.

Codex should not run destructive migrations, overwrite secrets, delete production data, or close issues without human review.
