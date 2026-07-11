from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable


def should_skip_dir(name: str, ignore_dirs: list[str]) -> bool:
    return name in set(ignore_dirs)


def as_posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def matches_any_glob(path: Path | str, patterns: list[str]) -> bool:
    p = as_posix(path)
    p_lower = p.lower()
    for pat in patterns:
        pat_norm = pat.replace("\\", "/")
        if fnmatch.fnmatch(p, pat_norm) or fnmatch.fnmatch(p_lower, pat_norm.lower()):
            return True
    return False


def is_protected(path: Path, config: dict) -> bool:
    return matches_any_glob(path, config.get("protected_globs", []))


def iter_files(roots: Iterable[Path], config: dict, suffixes: set[str] | None = None):
    ignore_dirs = set(config.get("ignore_dirs", []))
    ignore_globs = config.get("ignore_globs", [])
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames
                if d not in ignore_dirs and not matches_any_glob(Path(dirpath) / d, ignore_globs)
            ]
            for filename in filenames:
                p = Path(dirpath) / filename
                if matches_any_glob(p, ignore_globs):
                    continue
                if suffixes and p.suffix.lower() not in suffixes:
                    continue
                yield p


def rel_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")
