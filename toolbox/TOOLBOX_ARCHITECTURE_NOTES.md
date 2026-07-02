# QiLabs Toolbox Architecture Notes

## Correct model

```txt
toolbox.exe / toolbox_dynamic_ui.py
  = shell / launcher

toolbox_core
  = loader + validator + registry builder

tools/<category>/<tool_id>/
  = actual tools

manifest.yaml
  = tool contract
```

## Why this fixes rebuild pain

The built app should only contain:

- UI shell
- manifest loader
- registry builder
- validator
- subprocess launcher

The actual tools stay outside the binary. When you add a new folder under `tools/`, the shell sees it on refresh.

## Tool lifecycle

```txt
_pending
  → validate
  → active tools/category/tool_name
  → registry entry
  → visible in toolbox UI
```

## Registry files

Generated:

```txt
toolbox_registry.json
toolbox_validation_report.md
```

These are rebuildable outputs.

## What should not be committed or treated as source

Examples:

```txt
_housekeeping/plans/
_housekeeping/backups/
_housekeeping/logs/*.jsonl
_housekeeping/reports/*.json
_housekeeping/manifests/
_housekeeping/summaries/
tools/**/__pycache__/
tools/**/.pytest_cache/
toolbox_registry.json
toolbox_validation_report.md
```

Housekeeping output is runtime state, not source truth. Do not let Git become a junk drawer.
