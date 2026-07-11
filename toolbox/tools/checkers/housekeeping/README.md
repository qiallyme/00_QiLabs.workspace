# QiLabs Housekeeping Console

Interactive housekeeping console for QiLabs.

## Normal flow

1. Double-click `launch_housekeeping.bat`.
2. Click **Preview Full Run**.
3. Review the **Short Run Summary**.
4. Click **Approve + Apply**.
5. If the result is wrong, click **Undo Last Applied Run** before making unrelated edits.

## What changed in v0.4

- Adds a short summary panel so the first run is not a wall of text.
- Saves an apply manifest for every approved run.
- Adds one-click undo for the last applied run.
- Undo is safe-by-hash: if a file changed or moved after apply, that undo action is skipped and logged instead of bulldozing your work.
- Git commit/push is not auto-undone. Undo restores file changes into the working tree; it does not force-push or rewrite remote history.

## Key folders

```txt
_housekeeping/
  plans/       saved dry-run approval plans
  manifests/   apply manifests + undo manifests
  summaries/   short human-readable run summaries
  reports/     full detailed reports
  logs/        jsonl logs
  backups/     regular pre-apply backups
```

## The core safety model

```txt
Preview Full Run
→ save plan
→ approve
→ apply exact saved plan
→ save apply manifest
→ optional undo from manifest
```

## Undo behavior

Undo runs actions in reverse order.

- A modified existing file is restored from its manifest backup only if the current file still matches the apply hash.
- A file created by housekeeping is deleted only if it still matches the apply hash.
- A renamed file is renamed back only if the new path still exists, the original path is free, and the file still matches the apply hash.
- If any condition fails, that specific undo action is skipped and logged. The rest keep going.

That means undo is intentionally conservative. It should never “win” against newer work.
