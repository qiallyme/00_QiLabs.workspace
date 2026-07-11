from __future__ import annotations

from pathlib import Path
import json

STEP_NAME = "Generate report"


def _count_plan_actions(ctx) -> dict:
    planned = ctx.state.get("planned_actions", [])
    return {
        "planned_actions": len(planned),
        "planned_writes": sum(1 for a in planned if a.get("type") == "write_text"),
        "planned_renames": sum(1 for a in planned if a.get("type") == "rename"),
    }


def _apply_counts(ctx) -> dict:
    actions = ctx.state.get("apply_manifest_actions", [])
    return {
        "apply_actions_seen": len(actions),
        "applied_actions": sum(1 for a in actions if a.get("status") == "applied"),
        "skipped_actions": sum(1 for a in actions if a.get("status") != "applied"),
    }


def _status_label(ctx, summary: dict) -> str:
    if ctx.state.get("errors"):
        return "Needs review"
    if ctx.state.get("warnings"):
        return "Completed with warnings"
    if summary.get("planned_actions", 0) == 0 and ctx.dry_run:
        return "No file changes planned"
    return "OK"


def _build_summary(ctx) -> dict:
    summary = {
        "run_id": ctx.run_id,
        "mode": "dry-run" if ctx.dry_run else "apply",
        "allow_renames": ctx.allow_renames,
        "push_requested": ctx.push,
        **_count_plan_actions(ctx),
        **_apply_counts(ctx),
        "changed_files": len(ctx.state.get("changed_files", [])),
        "warnings": len(ctx.state.get("warnings", [])),
        "errors": len(ctx.state.get("errors", [])),
        "plan_file": str(getattr(ctx, "plan_file", "")),
        "apply_manifest_file": ctx.state.get("apply_manifest_file", ""),
        "undo_manifest_file": ctx.state.get("undo_manifest_file", ""),
        "report_file": str(ctx.report_file),
        "summary_file": str(ctx.summary_file),
    }
    summary["status"] = _status_label(ctx, summary)
    ctx.state["run_summary"] = summary
    return summary


def _write_short_summary(ctx, summary: dict) -> None:
    lines = []
    lines.append("# QiLabs Housekeeping Summary")
    lines.append("")
    lines.append(f"- Status: **{summary['status']}**")
    lines.append(f"- Run ID: `{ctx.run_id}`")
    lines.append(f"- Mode: `{summary['mode']}`")
    lines.append(f"- Planned actions: `{summary['planned_actions']}`")
    lines.append(f"- Planned writes: `{summary['planned_writes']}`")
    lines.append(f"- Planned renames: `{summary['planned_renames']}`")
    lines.append(f"- Applied actions: `{summary['applied_actions']}`")
    lines.append(f"- Skipped actions: `{summary['skipped_actions']}`")
    lines.append(f"- Changed files: `{summary['changed_files']}`")
    lines.append(f"- Warnings: `{summary['warnings']}`")
    lines.append(f"- Errors: `{summary['errors']}`")
    if summary.get("apply_manifest_file"):
        lines.append(f"- Apply manifest: `{summary['apply_manifest_file']}`")
    if summary.get("undo_manifest_file"):
        lines.append(f"- Undo manifest: `{summary['undo_manifest_file']}`")
    lines.append("")

    if ctx.state.get("warnings"):
        lines.append("## Top Warnings")
        lines.append("")
        for w in ctx.state["warnings"][:10]:
            lines.append(f"- {w}")
        lines.append("")
    if ctx.state.get("errors"):
        lines.append("## Top Errors")
        lines.append("")
        for e in ctx.state["errors"][:10]:
            lines.append(f"- {e}")
        lines.append("")

    if ctx.state.get("changed_files"):
        lines.append("## Changed Files")
        lines.append("")
        for p in ctx.state["changed_files"][:50]:
            lines.append(f"- `{p}`")
        if len(ctx.state["changed_files"]) > 50:
            lines.append(f"- ...and `{len(ctx.state['changed_files']) - 50}` more")
        lines.append("")

    lines.append("## Next Move")
    lines.append("")
    if summary["mode"] == "dry-run" and summary["errors"] == 0:
        lines.append("Review the full report, then approve/apply the saved plan if the summary looks sane.")
    elif summary["mode"] == "apply" and summary["applied_actions"] > 0:
        lines.append("If the result looks wrong, use **Undo Last Applied Run** before making more unrelated edits.")
    else:
        lines.append("Review warnings/errors before approving more changes.")

    ctx.summary_file.write_text("\n".join(lines), encoding="utf-8")


def run(ctx):
    summary = _build_summary(ctx)
    _write_short_summary(ctx, summary)

    lines = []
    lines.append("# QiLabs Housekeeping Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- Status: **{summary['status']}**")
    lines.append(f"- Run ID: `{ctx.run_id}`")
    lines.append(f"- Mode: `{'dry-run' if ctx.dry_run else 'apply'}`")
    lines.append(f"- Allow renames: `{ctx.allow_renames}`")
    lines.append(f"- Push requested: `{ctx.push}`")
    lines.append(f"- Planned actions: `{summary['planned_actions']}`")
    lines.append(f"- Planned writes: `{summary['planned_writes']}`")
    lines.append(f"- Planned renames: `{summary['planned_renames']}`")
    lines.append(f"- Applied actions: `{summary['applied_actions']}`")
    lines.append(f"- Skipped actions: `{summary['skipped_actions']}`")
    lines.append(f"- Changed files: `{summary['changed_files']}`")
    lines.append(f"- Warnings: `{summary['warnings']}`")
    lines.append(f"- Errors: `{summary['errors']}`")
    lines.append(f"- Summary file: `{ctx.summary_file}`")
    lines.append(f"- Plan file: `{getattr(ctx, 'plan_file', '')}`")
    if summary.get("apply_manifest_file"):
        lines.append(f"- Apply manifest: `{summary['apply_manifest_file']}`")
    if summary.get("undo_manifest_file"):
        lines.append(f"- Undo manifest: `{summary['undo_manifest_file']}`")
    lines.append("")

    lines.append("## Results")
    lines.append("")
    for result in ctx.state.get("results", []):
        step = result.get("step", "Unknown")
        lines.append(f"### {step}")
        lines.append("")
        for k, v in result.items():
            if k == "step":
                continue
            lines.append(f"- {k}: `{v}`")
        lines.append("")
    if ctx.state.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for w in ctx.state["warnings"]:
            lines.append(f"- {w}")
        lines.append("")
    if ctx.state.get("errors"):
        lines.append("## Errors")
        lines.append("")
        for e in ctx.state["errors"]:
            lines.append(f"- {e}")
        lines.append("")
    if ctx.state.get("planned_actions"):
        lines.append("## Planned Actions")
        lines.append("")
        for action in ctx.state["planned_actions"][:500]:
            label = action.get("description") or action.get("type")
            target = action.get("path") or action.get("old_path")
            lines.append(f"- `{action.get('type')}` — {label} — `{target}`")
        if len(ctx.state["planned_actions"]) > 500:
            lines.append(f"- ...and `{len(ctx.state['planned_actions']) - 500}` more planned actions")
        lines.append("")

    if ctx.state.get("apply_manifest_actions"):
        lines.append("## Apply Manifest Actions")
        lines.append("")
        for action in ctx.state["apply_manifest_actions"][:500]:
            label = action.get("description") or action.get("type")
            target = action.get("path") or action.get("new_path") or action.get("old_path")
            lines.append(f"- `{action.get('status')}` `{action.get('type')}` — {label} — `{target}`")
        lines.append("")

    if ctx.state.get("changed_files"):
        lines.append("## Changed Files")
        lines.append("")
        for p in ctx.state["changed_files"][:500]:
            lines.append(f"- `{p}`")
        lines.append("")
    if ctx.state.get("frontmatter_examples"):
        lines.append("## Frontmatter Examples")
        lines.append("")
        for item in ctx.state["frontmatter_examples"][:50]:
            lines.append(f"- `{item['path']}` added `{', '.join(item['added'])}`")
        lines.append("")

    ctx.report_file.write_text("\n".join(lines), encoding="utf-8")
    ctx.add_result(STEP_NAME, {"report_file": str(ctx.report_file), "summary_file": str(ctx.summary_file), "status": summary["status"]})
