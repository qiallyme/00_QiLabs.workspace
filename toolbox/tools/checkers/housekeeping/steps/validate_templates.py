from pathlib import Path
from core.frontmatter import split_frontmatter, parse_frontmatter_keys

STEP_NAME = "Validate master template"

def run(ctx):
    template_path = Path(ctx.config["master_template_file"])
    if not template_path.exists():
        ctx.warn(f"Master template missing: {template_path}")
        ctx.add_result(STEP_NAME, {"status": "missing"})
        return

    text = template_path.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(text)
    keys = parse_frontmatter_keys(fm)
    required = ctx.config.get("frontmatter", {}).get("required_base_keys", [])
    missing = [k for k in required if k not in keys]

    if missing:
        ctx.warn(f"Master template missing configured keys: {missing}")
    if "created_at" in keys and "last_updated" not in keys:
        ctx.info("Template uses created_at/updated_at. Other docs using last_updated should be mapped, not overwritten.")

    ctx.state["master_template_keys"] = list(keys.keys())
    ctx.add_result(STEP_NAME, {
        "template_keys": len(keys),
        "missing_required_keys": len(missing),
        "path": str(template_path)
    })
