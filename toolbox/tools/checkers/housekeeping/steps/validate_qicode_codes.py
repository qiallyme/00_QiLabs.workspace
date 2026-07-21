from pathlib import Path
import re
from core.fs import rel_to_root
from core.frontmatter import parse_frontmatter_keys, split_frontmatter, normalize_text_for_frontmatter

STEP_NAME = "Validate QiCode codes"

def run(ctx):
    qilabs_root = Path(ctx.config["qilabs_root"])
    qicode_root = Path(r"C:\QiLabs\40_QiVault\00_home\00_QiCode")
    
    scanned = 0
    errors = []

    for p in qicode_root.rglob("*.md"):
        if not p.is_file(): continue
        scanned += 1
        text = normalize_text_for_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        fm, body = split_frontmatter(text)
        if not fm:
            errors.append(f"{p.name}: No frontmatter found")
            continue
            
        keys = parse_frontmatter_keys(fm)
        stable_id = str(keys.get("stable_id", "")).strip()
        
        if not stable_id:
            errors.append(f"{p.name}: Missing stable_id")
            continue
            
        name = p.name
        
        # Check patterns based on file name or type
        if "title_" in name and not "article_" in name:
            if not re.match(r"^T\d{2}$", stable_id):
                errors.append(f"{p.name}: Invalid title stable_id '{stable_id}'. Expected TXX.")
        elif "article_" in name:
            if not re.match(r"^T\d{2}\.A\d{2}$", stable_id):
                errors.append(f"{p.name}: Invalid article stable_id '{stable_id}'. Expected TXX.AXX.")

        # Check body citation match (just basic verification that it contains a section or symbol)
        if "§" not in body and "article_" in name:
            errors.append(f"{p.name}: No § symbol found in article body")

    ctx.add_result(STEP_NAME, {
        "qicode_scanned": scanned,
        "validation_errors": len(errors),
        "errors": errors[:20]
    })
    
    if errors:
        for err in errors[:20]:
            ctx.warning(f"QiCode Validation Error: {err}")
