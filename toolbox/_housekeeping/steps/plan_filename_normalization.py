from pathlib import Path
import json
from core.fs import iter_files, is_protected, rel_to_root
from core.naming import normalized_markdown_filename, should_consider_for_rename

STEP_NAME = "Plan filename normalization"

def run(ctx):
    roots = [Path(p) for p in ctx.config.get("default_scope_roots", [])]
    qilabs_root = Path(ctx.config["qilabs_root"])
    plan = []
    conflicts = []
    protected_skipped = 0

    for p in iter_files(roots, ctx.config, suffixes={".md"}):
        if is_protected(p, ctx.config):
            protected_skipped += 1
            continue
        if not should_consider_for_rename(p, ctx.config):
            continue
        new_name = normalized_markdown_filename(p, ctx.config)
        if new_name != p.name:
            target = p.with_name(new_name)
            item = {
                "old": rel_to_root(p, qilabs_root),
                "new": rel_to_root(target, qilabs_root),
                "old_abs": str(p),
                "new_abs": str(target)
            }
            if target.exists():
                conflicts.append(item)
            else:
                plan.append(item)

    ctx.rename_plan_file.write_text(json.dumps({"plan": plan, "conflicts": conflicts}, indent=2, ensure_ascii=False), encoding="utf-8")
    ctx.state["rename_plan"] = plan
    # Only expose rename_map to later link-rewrite steps when renames are actually included.
    # This prevents a dry-run that merely *reports* rename candidates from planning link rewrites for renames that will not apply.
    ctx.state["rename_map"] = {item["old"]: item["new"] for item in plan} if ctx.allow_renames else {}

    if conflicts:
        ctx.warn(f"Filename rename conflicts found: {len(conflicts)}")

    if ctx.dry_run:
        if ctx.allow_renames:
            for item in plan:
                ctx.plan_rename(Path(item["old_abs"]), Path(item["new_abs"]), STEP_NAME, description="Normalize Markdown filename")
            planned = len(plan)
        else:
            planned = 0
            if plan:
                ctx.warn("Filename rename candidates found, but they are not included in this plan because Include filename renames is unchecked.")
        ctx.add_result(STEP_NAME, {
            "rename_candidates": len(plan),
            "conflicts": len(conflicts),
            "renames_planned": planned,
            "renames_applied": 0,
            "protected_skipped": protected_skipped,
            "rename_plan_file": str(ctx.rename_plan_file)
        })
    elif ctx.allow_renames:
        applied = 0
        for item in plan:
            old = Path(item["old_abs"])
            new = Path(item["new_abs"])
            if old.exists() and not new.exists():
                ctx.backup_file(old)
                old.rename(new)
                ctx.mark_changed(new)
                applied += 1
                ctx.info(f"Renamed {old} -> {new}")
        ctx.add_result(STEP_NAME, {
            "rename_candidates": len(plan),
            "conflicts": len(conflicts),
            "renames_planned": 0,
            "renames_applied": applied,
            "protected_skipped": protected_skipped,
            "rename_plan_file": str(ctx.rename_plan_file)
        })
    else:
        ctx.warn("Apply mode is active, but filename renames are blocked because Include filename renames is unchecked.")
        ctx.add_result(STEP_NAME, {
            "rename_candidates": len(plan),
            "conflicts": len(conflicts),
            "renames_planned": 0,
            "renames_applied": 0,
            "protected_skipped": protected_skipped,
            "rename_plan_file": str(ctx.rename_plan_file)
        })
