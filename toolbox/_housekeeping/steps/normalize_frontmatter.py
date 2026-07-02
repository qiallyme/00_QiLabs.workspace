from pathlib import Path
from core.fs import iter_files, is_protected, rel_to_root
from core.frontmatter import add_missing_frontmatter

STEP_NAME = "Normalize frontmatter"

def run(ctx):
    roots = [Path(p) for p in ctx.config.get("default_scope_roots", [])]
    qilabs_root = Path(ctx.config["qilabs_root"])
    fm_cfg = ctx.config.get("frontmatter", {})
    required = fm_cfg.get("required_base_keys", [])
    defaults = fm_cfg.get("default_values", {})
    dynamic = fm_cfg.get("dynamic_keys_by_type", {})

    scanned = changed = protected_skipped = 0
    added_keys_total = 0
    examples = []

    for p in iter_files(roots, ctx.config, suffixes={".md"}):
        scanned += 1
        if is_protected(p, ctx.config):
            protected_skipped += 1
            continue

        text = p.read_text(encoding="utf-8", errors="replace")
        new_text, added = add_missing_frontmatter(text, p, required, defaults, dynamic)
        if added:
            changed += 1
            added_keys_total += len(added)
            examples.append({"path": rel_to_root(p, qilabs_root), "added": added})
            ctx.info(f"{'Would update' if ctx.dry_run else 'Updating'} frontmatter: {p} +{added}")
            if ctx.dry_run:
                ctx.plan_write_text(p, new_text, STEP_NAME, description=f"Add missing frontmatter keys: {', '.join(added)}")
            else:
                ctx.backup_file(p)
                p.write_text(new_text, encoding="utf-8")
                ctx.mark_changed(p)

    ctx.state["frontmatter_examples"] = examples[:50]
    ctx.add_result(STEP_NAME, {
        "markdown_scanned": scanned,
        "files_with_missing_keys": changed,
        "keys_added_total": added_keys_total,
        "protected_skipped": protected_skipped,
        "mode": "dry-run" if ctx.dry_run else "apply"
    })
