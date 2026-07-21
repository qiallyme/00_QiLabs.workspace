from pathlib import Path
from core.fs import iter_files, rel_to_root
from core.frontmatter import get_frontmatter_keys_from_file

STEP_NAME = "Validate QiCode frontmatter"

def run(ctx):
    qilabs_root = Path(ctx.config["qilabs_root"])
    qicode_root = Path(r"C:\QiLabs\40_QiVault\00_home\00_QiCode")
    fm_cfg = ctx.config.get("frontmatter", {})
    
    required = fm_cfg.get("required_base_keys", [])
    qicode_profile = fm_cfg.get("qicode_profile", {})
    qicode_required = qicode_profile.get("required_keys", [])
    
    # Merge required
    merged_required = required + [k for k in qicode_required if k not in required]

    scanned = 0
    missing_by_file = {}

    for p in qicode_root.rglob("*.md"):
        if not p.is_file(): continue
        
        scanned += 1
        keys = get_frontmatter_keys_from_file(p)
        missing = [k for k in merged_required if k not in keys]
        
        if missing:
            rel = rel_to_root(p, qilabs_root)
            missing_by_file[rel] = missing
            ctx.warning(f"QiCode Frontmatter Validation Error: {p.name} is missing keys: {missing}")

    ctx.add_result(STEP_NAME, {
        "qicode_scanned": scanned,
        "files_with_missing_keys": len(missing_by_file),
        "missing_examples": {k: v for i, (k, v) in enumerate(missing_by_file.items()) if i < 20}
    })
