from pathlib import Path
from core.fs import iter_files, rel_to_root
from core.frontmatter import add_missing_frontmatter

STEP_NAME = "Normalize QiCode frontmatter"

def run(ctx):
    qilabs_root = Path(ctx.config["qilabs_root"])
    qicode_root = Path(r"C:\QiLabs\40_QiVault\00_home\00_QiCode")
    fm_cfg = ctx.config.get("frontmatter", {})
    
    # Base requirements
    required = fm_cfg.get("required_base_keys", [])
    defaults = fm_cfg.get("default_values", {})
    
    # QiCode specific requirements
    qicode_profile = fm_cfg.get("qicode_profile", {})
    qicode_defaults = qicode_profile.get("defaults", {})
    qicode_required = qicode_profile.get("required_keys", [])
    
    # Merge defaults and required
    merged_defaults = {**defaults, **qicode_defaults}
    merged_required = required + [k for k in qicode_required if k not in required]
    
    dynamic = fm_cfg.get("dynamic_keys_by_type", {})

    scanned = changed = 0
    added_keys_total = 0
    examples = []

    # Iter files but bypass protected_globs since we strictly target QiCode
    for p in qicode_root.rglob("*.md"):
        if not p.is_file(): continue
        
        scanned += 1
        text = p.read_text(encoding="utf-8", errors="replace")
        new_text, added = add_missing_frontmatter(text, p, merged_required, merged_defaults, dynamic)
        
        if added:
            changed += 1
            added_keys_total += len(added)
            examples.append({"path": rel_to_root(p, qilabs_root), "added": added})
            ctx.info(f"{'Would update' if ctx.dry_run else 'Updating'} QiCode frontmatter: {p.name} +{added}")
            if ctx.dry_run:
                ctx.plan_write_text(p, new_text, STEP_NAME, description=f"Add missing QiCode keys: {', '.join(added)}")
            else:
                ctx.backup_file(p)
                with p.open("w", encoding="utf-8", newline="") as f:
                    f.write(new_text)
                ctx.mark_changed(p)

    ctx.state["qicode_frontmatter_examples"] = examples[:50]
    ctx.add_result(STEP_NAME, {
        "qicode_scanned": scanned,
        "files_with_missing_keys": changed,
        "keys_added_total": added_keys_total,
        "mode": "dry-run" if ctx.dry_run else "apply"
    })
