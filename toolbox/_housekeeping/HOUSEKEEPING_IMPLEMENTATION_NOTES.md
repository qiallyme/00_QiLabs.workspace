# Housekeeping Implementation Notes

## UX model

The console now has two lanes:

1. **Full Run Workflow** — normal path.
   - Preview full run.
   - Review short summary.
   - Approve/apply the saved plan.
   - Optional undo last applied run.

2. **Manual Step Mode** — surgery mode.
   - Preview one step.
   - Approve that step's saved plan.
   - Cancel if it looks wrong.

## Run manifests

Every apply run writes:

```txt
_housekeeping/manifests/apply-manifest-<run_id>.json
_housekeeping/manifests/latest_apply_manifest.json
```

The apply manifest contains:

- source preview plan
- applied/skipped counts
- before/after hashes
- backup payload pointers
- per-action undo instructions
- warnings/errors
- report/log paths

## Undo manifests

Every undo run writes:

```txt
_housekeeping/manifests/undo-manifest-<run_id>.json
```

The undo manifest records what was undone and what was skipped.

## Hash safety

Apply verifies preview-time hashes before writing.
Undo verifies apply-time hashes before restoring/deleting/renaming.

This is the important part: if Cody moves or edits something after a run, undo skips that item and keeps going. No tantrums, no overwrites.

## Git limitation

File undo is supported. Git history undo is not automatic.

If a run was committed or pushed, undo restores files into the working tree. It does not rewrite commits, force-push, or remote-revert. That should remain manual unless a separate Git Revert tool is built.
