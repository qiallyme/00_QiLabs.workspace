from __future__ import annotations

import datetime
from pathlib import Path
from core.git_utils import build_manifest, write_manifest
import json

STEP_NAME = "Update Git manifest"


def run(ctx):
    git_cfg = ctx.config.get("git", {})
    roots = git_cfg.get("discover_roots") or ctx.config.get("git_roots", [])
    manifest = build_manifest(
        roots,
        ignore_dirs=ctx.config.get("ignore_dirs", []),
        qilabs_root=ctx.config.get("qilabs_root")
    )
    manifest["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    manifest["manifest_note"] = "Generated from live .git folders and git remote config; do not hand-maintain URLs."

    paths = [git_cfg.get("manifest_file")] + git_cfg.get("manifest_mirror_files", [])
    paths = [p for p in paths if p]

    dirty = sum(1 for r in manifest["repos"] if r.get("dirty"))
    ahead = sum(1 for r in manifest["repos"] if r.get("ahead", 0) > 0)
    no_origin = [r["relative_path"] for r in manifest["repos"] if not r.get("origin_url")]

    for r in manifest["repos"]:
        ctx.info(f"Repo: {r['relative_path']} | branch={r['branch']} | dirty={r['dirty']} | ahead={r['ahead']} | origin={r.get('origin_url') or '[none]'}")

    if no_origin:
        ctx.warn(f"Repos without origin remote: {no_origin}")

    if ctx.dry_run:
        manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False)
        for raw in paths:
            ctx.plan_write_text(Path(raw), manifest_text, STEP_NAME, description="Regenerate live Git manifest from discovered repos/remotes")
        ctx.info(f"Planned Git manifest write to: {paths}")
    else:
        # Backup existing manifest files before regenerating.
        for raw in paths:
            p = Path(raw)
            if p.exists():
                ctx.backup_file(p)
        written = write_manifest(manifest, paths)
        for raw in written:
            ctx.mark_changed(Path(raw))
        ctx.info(f"Wrote Git manifest to: {written}")

    ctx.state["git_manifest"] = manifest
    ctx.add_result(STEP_NAME, {
        "repos_found": manifest["repo_count"],
        "dirty_repos": dirty,
        "ahead_repos": ahead,
        "manifest_paths": paths,
        "mode": "dry-run" if ctx.dry_run else "apply"
    })
