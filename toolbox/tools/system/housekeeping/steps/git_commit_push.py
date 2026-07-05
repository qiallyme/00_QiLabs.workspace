from __future__ import annotations

import datetime
from pathlib import Path
from core.git_utils import (
    discover_git_repos,
    git_status,
    git,
    ahead_behind,
    upstream_name,
    current_branch,
    stage_filtered,
)

STEP_NAME = "Recursive Git commit / push"


def push_repo(ctx, repo: Path, set_upstream: bool) -> bool:
    branch = current_branch(repo)
    upstream = upstream_name(repo)
    if upstream:
        code, out = git(repo, ["push"])
    elif set_upstream and branch and not branch.startswith("detached:") and branch != "unknown":
        code, out = git(repo, ["push", "-u", "origin", branch])
    else:
        ctx.warn(f"No upstream for {repo}; skipping push. Set an upstream or add origin/branch.")
        return False

    if code != 0:
        ctx.error(f"git push failed in {repo}: {out}")
        return False
    ctx.info(f"Pushed {repo}")
    return True


def run(ctx):
    git_cfg = ctx.config.get("git", {})
    roots = git_cfg.get("discover_roots") or ctx.config.get("git_roots", [])
    repos = discover_git_repos(roots, ignore_dirs=ctx.config.get("ignore_dirs", []))

    if not repos:
        ctx.warn("No Git repos found. Skipping git step.")
        ctx.add_result(STEP_NAME, {"status": "skipped no repos"})
        return

    # Deepest first lets child repos commit/push before the parent records submodule/gitlink changes.
    repos = sorted(repos, key=lambda p: len(p.parts), reverse=True)
    msg = f"{git_cfg.get('commit_message_prefix', 'chore: housekeeping')} {datetime.datetime.now().strftime('%Y-%m-%d')}"

    summary = []
    for repo in repos:
        status = git_status(repo)
        ahead, _behind = ahead_behind(repo)
        ctx.info(f"Git repo: {repo} | dirty={bool(status)} | ahead={ahead}")

        if ctx.dry_run:
            summary.append({"repo": str(repo), "dirty": bool(status), "ahead": ahead, "would_commit": bool(status), "would_push": bool(ctx.push and (status or ahead))})
            continue

        committed = False
        pushed = False
        skipped_nested = []

        if status:
            code, out, skipped_nested = stage_filtered(
                repo,
                repos,
                skip_unregistered_nested=git_cfg.get("skip_unregistered_nested_repos_in_parent", True)
            )
            if skipped_nested:
                ctx.warn(f"Skipped unregistered nested repo paths while staging {repo}: {skipped_nested[:20]}")
            if code != 0:
                ctx.error(f"git add failed in {repo}: {out}")
                summary.append({"repo": str(repo), "committed": False, "pushed": False, "error": "git add failed"})
                continue

            # Re-check staged changes. Some dirty status may have been only skipped nested repos.
            code, staged = git(repo, ["diff", "--cached", "--name-only"])
            if code == 0 and staged.strip():
                code, out = git(repo, ["commit", "-m", msg])
                if code != 0:
                    ctx.error(f"git commit failed in {repo}: {out}")
                    summary.append({"repo": str(repo), "committed": False, "pushed": False, "error": "git commit failed"})
                    continue
                committed = True
                ctx.info(f"Committed {repo}: {msg}")
            else:
                ctx.info(f"No parent-owned staged changes for {repo} after nested repo filtering.")

        ahead_after, _behind_after = ahead_behind(repo)
        should_push = ctx.push and (committed or ahead_after > 0 or git_cfg.get("push_clean_repos_with_ahead_commits", True) and ahead > 0)
        if should_push:
            pushed = push_repo(ctx, repo, git_cfg.get("set_upstream_when_missing", True))

        summary.append({
            "repo": str(repo),
            "committed": committed,
            "pushed": pushed,
            "skipped_nested_paths": skipped_nested[:50],
        })

    ctx.add_result(STEP_NAME, {
        "repos_seen": len(repos),
        "mode": "dry-run" if ctx.dry_run else "apply",
        "push_requested": ctx.push,
        "summary": summary
    })
