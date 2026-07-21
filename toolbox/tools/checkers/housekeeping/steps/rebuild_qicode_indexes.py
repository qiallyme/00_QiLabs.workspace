from pathlib import Path
from core.fs import iter_files

STEP_NAME = "Rebuild QiCode indexes"

def run(ctx):
    qicode_root = Path(r"C:\QiLabs\40_QiVault\00_home\00_QiCode")
    idx_cfg = ctx.config.get("indexing", {})
    index_name = idx_cfg.get("index_filename", "_index.md")
    start = idx_cfg.get("managed_block_start")
    end = idx_cfg.get("managed_block_end")
    max_items = int(idx_cfg.get("max_items_per_folder", 200))

    folders = set()
    for p in qicode_root.rglob("*.md"):
        if p.is_file():
            folders.add(p.parent)

    created = updated = skipped = 0

    for folder in sorted(folders):
        md_files = sorted([f.name for f in folder.glob("*.md") if f.name != index_name])[:max_items]
        if not md_files:
            continue

        block = [start, "", "## QiCode Index", ""]
        for name in md_files:
            label = Path(name).stem.replace("-", " ").replace("_", " ")
            block.append(f"- [[{Path(name).stem}|{label}]]")
        block += ["", end, ""]
        block_text = "\n".join(block)

        index_path = folder / index_name
        if index_path.exists():
            text = index_path.read_text(encoding="utf-8", errors="replace")
            if start in text and end in text:
                before = text.split(start)[0].rstrip()
                after = text.split(end, 1)[1].lstrip()
                new_text = before + "\n\n" + block_text + "\n" + after
                if new_text != text:
                    updated += 1
                    ctx.info(f"{'Would update' if ctx.dry_run else 'Updating'} QiCode managed index block: {index_path}")
                    if ctx.dry_run:
                        ctx.plan_write_text(index_path, new_text, STEP_NAME, description="Update managed folder index block in QiCode")
                    else:
                        ctx.backup_file(index_path)
                        index_path.write_text(new_text, encoding="utf-8")
                        ctx.mark_changed(index_path)
            else:
                updated += 1
                ctx.info(f"{'Would append' if ctx.dry_run else 'Appending'} QiCode managed index block: {index_path}")
                new_text = text.rstrip() + "\n\n" + block_text
                if ctx.dry_run:
                    ctx.plan_write_text(index_path, new_text, STEP_NAME, description="Append managed folder index block in QiCode")
                else:
                    ctx.backup_file(index_path)
                    index_path.write_text(new_text, encoding="utf-8")
                    ctx.mark_changed(index_path)
        else:
            created += 1
            ctx.info(f"{'Would create' if ctx.dry_run else 'Creating'} QiCode index: {index_path}")
            content = f"---\ntitle: \"{folder.name}\"\ntype: index\nstatus: active\ngenerated_by: qilabs-housekeeping\ngenerated_at: \"{ctx.run_id}\"\n---\n\n# {folder.name}\n\n{block_text}"
            if ctx.dry_run:
                ctx.plan_write_text(index_path, content, STEP_NAME, description="Create QiCode folder index")
            else:
                index_path.write_text(content, encoding="utf-8")
                ctx.mark_changed(index_path)

    ctx.add_result(STEP_NAME, {
        "qicode_folders_seen": len(folders),
        "indexes_created": created,
        "indexes_updated_or_appended": updated
    })
