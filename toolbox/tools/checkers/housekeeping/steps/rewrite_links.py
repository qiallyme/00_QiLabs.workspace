from pathlib import Path
from core.fs import iter_files, is_protected
from core.links import rewrite_wikilinks, rewrite_markdown_links

STEP_NAME = "Rewrite links"

def run(ctx):
    rename_map = ctx.state.get("rename_map", {})
    if not rename_map:
        ctx.warn("No rename map found in this run. Run filename normalization first, or this step has nothing to do.")
        ctx.add_result(STEP_NAME, {"files_scanned": 0, "links_rewritten": 0})
        return

    roots = [Path(p) for p in ctx.config.get("default_scope_roots", [])]
    scanned = files_changed = links_changed = protected_skipped = 0

    for p in iter_files(roots, ctx.config, suffixes={".md"}):
        scanned += 1
        if is_protected(p, ctx.config):
            protected_skipped += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        text2, c1 = rewrite_wikilinks(text, rename_map)
        text3, c2 = rewrite_markdown_links(text2, rename_map)
        total = c1 + c2
        if total:
            files_changed += 1
            links_changed += total
            ctx.info(f"{'Would rewrite' if ctx.dry_run else 'Rewriting'} {total} link(s): {p}")
            if ctx.dry_run:
                ctx.plan_write_text(p, text3, STEP_NAME, description=f"Rewrite {total} link(s) from rename map")
            else:
                ctx.backup_file(p)
                p.write_text(text3, encoding="utf-8")
                ctx.mark_changed(p)

    ctx.add_result(STEP_NAME, {
        "files_scanned": scanned,
        "files_changed": files_changed,
        "links_rewritten": links_changed,
        "protected_skipped": protected_skipped
    })
