from __future__ import annotations

import configparser
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, shell=False)
    return p.returncode, (p.stdout + p.stderr).strip()


def git(root: Path, args: list[str]) -> tuple[int, str]:
    return run(["git", *args], root)


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def find_git_root(candidates: list[str]) -> Path | None:
    for c in candidates:
        p = Path(c)
        if is_git_repo(p):
            return p
    return None


def git_status(root: Path) -> str:
    code, out = git(root, ["status", "--short"])
    if code != 0:
        return out or "git status failed"
    return out


def current_branch(root: Path) -> str:
    code, out = git(root, ["branch", "--show-current"])
    if code == 0 and out.strip():
        return out.strip()
    code, out = git(root, ["rev-parse", "--short", "HEAD"])
    return f"detached:{out.strip()}" if code == 0 and out.strip() else "unknown"


def current_head(root: Path) -> str:
    code, out = git(root, ["rev-parse", "HEAD"])
    return out.strip() if code == 0 else ""


def upstream_name(root: Path) -> str:
    code, out = git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    return out.strip() if code == 0 else ""


def ahead_behind(root: Path) -> tuple[int, int]:
    if not upstream_name(root):
        return (0, 0)
    code, out = git(root, ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    if code != 0:
        return (0, 0)
    parts = out.split()
    if len(parts) >= 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return (0, 0)
    return (0, 0)


def remotes(root: Path) -> dict[str, dict[str, str]]:
    code, out = git(root, ["remote", "-v"])
    data: dict[str, dict[str, str]] = {}
    if code != 0:
        return data
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            name, url, kind = parts[0], parts[1], parts[2].strip("()")
            data.setdefault(name, {})[kind] = url
    return data


def origin_url(root: Path) -> str:
    rs = remotes(root)
    return rs.get("origin", {}).get("fetch") or rs.get("origin", {}).get("push") or ""


def superproject(root: Path) -> str:
    code, out = git(root, ["rev-parse", "--show-superproject-working-tree"])
    return out.strip() if code == 0 else ""


def discover_git_repos(search_roots: list[str], ignore_dirs: list[str] | None = None) -> list[Path]:
    ignore = set(ignore_dirs or [])
    found: set[Path] = set()
    for raw in search_roots:
        start = Path(raw)
        if not start.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(start):
            p = Path(dirpath)
            dirnames[:] = [d for d in dirnames if d not in ignore and d != ".git"]
            if (p / ".git").exists():
                found.add(p.resolve())
    return sorted(found, key=lambda p: (len(p.parts), str(p).lower()), reverse=True)


def registered_submodule_paths(root: Path) -> set[str]:
    gm = root / ".gitmodules"
    if not gm.exists():
        return set()
    parser = configparser.ConfigParser()
    try:
        parser.read(gm, encoding="utf-8")
    except Exception:
        return set()
    out = set()
    for section in parser.sections():
        if parser.has_option(section, "path"):
            out.add(parser.get(section, "path").replace("\\", "/").strip("/"))
    return out


def nested_repo_paths_for_parent(parent: Path, repos: list[Path]) -> set[str]:
    out: set[str] = set()
    parent_resolved = parent.resolve()
    for repo in repos:
        repo_resolved = repo.resolve()
        if repo_resolved == parent_resolved:
            continue
        try:
            rel = repo_resolved.relative_to(parent_resolved).as_posix()
            out.add(rel)
        except Exception:
            pass
    return out


def status_paths(root: Path) -> list[str]:
    code, out = git(root, ["status", "--porcelain=v1"])
    if code != 0 or not out:
        return []
    paths: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            old, new = raw.split(" -> ", 1)
            paths.extend([old.strip('"'), new.strip('"')])
        else:
            paths.append(raw.strip('"'))
    return paths


def path_is_under(path: str, root_rel: str) -> bool:
    path = path.replace("\\", "/").strip("/")
    root_rel = root_rel.replace("\\", "/").strip("/")
    return path == root_rel or path.startswith(root_rel + "/")


def stage_filtered(root: Path, all_repos: list[Path], skip_unregistered_nested: bool = True) -> tuple[int, str, list[str]]:
    nested = nested_repo_paths_for_parent(root, all_repos)
    registered = registered_submodule_paths(root)
    paths = status_paths(root)
    skipped: list[str] = []

    if skip_unregistered_nested and nested:
        filtered = []
        for p in paths:
            nested_hit = next((n for n in nested if path_is_under(p, n)), None)
            if nested_hit and nested_hit not in registered:
                skipped.append(p)
                continue
            filtered.append(p)
        paths = filtered

    if not paths:
        return 0, "No parent-owned paths to stage.", skipped

    # Batch to avoid command length issues.
    output_parts = []
    for i in range(0, len(paths), 50):
        batch = paths[i:i + 50]
        code, out = git(root, ["add", "-A", "--", *batch])
        output_parts.append(out)
        if code != 0:
            return code, "\n".join(output_parts), skipped
    return 0, "\n".join(output_parts).strip(), skipped


def repo_record(root: Path, qilabs_root: Path | None = None) -> dict[str, Any]:
    status = git_status(root)
    ahead, behind = ahead_behind(root)
    rel = str(root)
    if qilabs_root:
        try:
            rel = root.resolve().relative_to(qilabs_root.resolve()).as_posix()
        except Exception:
            pass
    return {
        "path": str(root),
        "relative_path": rel,
        "name": root.name,
        "branch": current_branch(root),
        "head": current_head(root),
        "upstream": upstream_name(root),
        "ahead": ahead,
        "behind": behind,
        "dirty": bool(status),
        "status_lines": len(status.splitlines()) if status else 0,
        "origin_url": origin_url(root),
        "remotes": remotes(root),
        "superproject": superproject(root),
        "registered_submodules": sorted(registered_submodule_paths(root)),
    }


def build_manifest(search_roots: list[str], ignore_dirs: list[str] | None = None, qilabs_root: str | None = None) -> dict[str, Any]:
    repos = discover_git_repos(search_roots, ignore_dirs=ignore_dirs)
    qroot = Path(qilabs_root) if qilabs_root else None
    return {
        "schema_version": "1.0",
        "generated_by": "qilabs-housekeeping",
        "repo_count": len(repos),
        "repos": [repo_record(repo, qroot) for repo in repos],
    }


def write_manifest(manifest: dict[str, Any], paths: list[str]) -> list[str]:
    written = []
    for raw in paths:
        p = Path(raw)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(str(p))
    return written
