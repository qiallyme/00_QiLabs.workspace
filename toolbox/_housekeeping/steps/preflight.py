from pathlib import Path
from core.git_utils import find_git_root, git_status

STEP_NAME = "Preflight"

def run(ctx):
    ctx.info("Running preflight checks")
    required = ["qilabs_root", "workspace_root", "vault_root", "tree_file", "master_template_file", "tags_file"]
    missing = []
    for key in required:
        p = Path(ctx.config[key])
        if not p.exists():
            missing.append(f"{key}: {p}")
            ctx.warn(f"Missing configured path: {key} -> {p}")
        else:
            ctx.info(f"Found {key}: {p}")

    git_root = find_git_root(ctx.config.get("git_roots", []))
    if git_root:
        ctx.state["git_root"] = str(git_root)
        status = git_status(git_root)
        if status:
            ctx.warn("Git working tree has changes. Review before apply/push.")
            ctx.state["git_status"] = status
        else:
            ctx.info("Git working tree appears clean.")
    else:
        ctx.warn("No .git folder found in configured git_roots. Git commit/push step will skip.")

    ctx.add_result(STEP_NAME, {
        "missing_paths": len(missing),
        "git_root": ctx.state.get("git_root", ""),
        "mode": "dry-run" if ctx.dry_run else "apply"
    })
