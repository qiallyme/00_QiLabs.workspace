from pathlib import Path
import os
import datetime
from core.fs import matches_any_glob

STEP_NAME = "Update QiLabs full tree"

def should_skip(path: Path, config: dict) -> bool:
    if path.name in set(config.get("ignore_dirs", [])):
        return True
    return matches_any_glob(path, config.get("ignore_globs", []))

def render_tree(root: Path, config: dict) -> list[str]:
    lines = [f"# {root.name}", ""]
    def walk(folder: Path, depth: int):
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            return
        for p in entries:
            if should_skip(p, config):
                continue
            indent = "  " * depth
            if p.is_dir():
                lines.append(f"{indent}- **{p.name}/**")
                walk(p, depth + 1)
            else:
                lines.append(f"{indent}- {p.name}")
    walk(root, 0)
    return lines

def run(ctx):
    root = Path(ctx.config["qilabs_root"])
    tree_file = Path(ctx.config["tree_file"])
    if not root.exists():
        ctx.warn(f"QiLabs root missing: {root}")
        ctx.add_result(STEP_NAME, {"status": "missing root"})
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d")
    frontmatter = f"""---
title: QiLabs Full Tree
section: qilabs/40_qivault/nav
access_level: L1
visibility: private
ai_ingest: true
status: active
last_updated: {now}
generated_by: qilabs-housekeeping
generated_at: "{ctx.run_id}"
---

"""
    lines = render_tree(root, ctx.config)
    new_text = frontmatter + "\n".join(lines) + "\n"

    ctx.info(f"{'Would update' if ctx.dry_run else 'Updating'} full tree file: {tree_file}")
    if ctx.dry_run:
        ctx.plan_write_text(tree_file, new_text, STEP_NAME, description="Regenerate QiLabs full tree")
    else:
        tree_file.parent.mkdir(parents=True, exist_ok=True)
        if tree_file.exists():
            ctx.backup_file(tree_file)
        tree_file.write_text(new_text, encoding="utf-8")
        ctx.mark_changed(tree_file)

    ctx.add_result(STEP_NAME, {
        "tree_file": str(tree_file),
        "lines_generated": len(lines),
        "mode": "dry-run" if ctx.dry_run else "apply"
    })
