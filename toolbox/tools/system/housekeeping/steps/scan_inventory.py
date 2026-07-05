from pathlib import Path
import json
from core.fs import iter_files, is_protected, rel_to_root

STEP_NAME = "Scan inventory"

def run(ctx):
    ctx.info("Scanning configured scope roots")
    roots = [Path(p) for p in ctx.config.get("default_scope_roots", [])]
    qilabs_root = Path(ctx.config["qilabs_root"])
    inventory = []
    ext_counts = {}
    protected_count = 0

    for p in iter_files(roots, ctx.config):
        ext = p.suffix.lower() or "[none]"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        protected = is_protected(p, ctx.config)
        if protected:
            protected_count += 1
        inventory.append({
            "path": rel_to_root(p, qilabs_root),
            "name": p.name,
            "extension": ext,
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "protected": protected
        })

    ctx.inventory_file.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    ctx.state["inventory"] = inventory
    ctx.add_result(STEP_NAME, {
        "files_scanned": len(inventory),
        "markdown_files": ext_counts.get(".md", 0),
        "json_files": ext_counts.get(".json", 0),
        "csv_files": ext_counts.get(".csv", 0),
        "protected_files": protected_count,
        "inventory_file": str(ctx.inventory_file)
    })
