from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import uuid
import subprocess
import datetime


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
GIT_DIRTY_CACHE: dict[Path, set[str]] = {}  # git_root -> set of relative dirty paths
GIT_HISTORY_CACHE: dict[Path, dict[str, tuple[str, str]]] = {} # git_root -> { rel_path -> (created_at, updated_at) }


def normalize_text_for_frontmatter(text: str) -> str:
    """Remove encoding markers that prevent frontmatter from being detected at the first byte."""
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


def read_text_no_bom(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def split_frontmatter(text: str):
    text = normalize_text_for_frontmatter(text)
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def parse_frontmatter_keys(fm: str | None) -> dict[str, str]:
    if not fm:
        return {}
    out: dict[str, str] = {}
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out


def value_to_yaml(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(str(x) for x in value) + "]"
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    s = str(value)
    if s == "":
        return '""'
    if any(ch in s for ch in [":", "#", "{", "}", "[", "]"]) or s.strip() != s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def title_from_filename(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[_-]?", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    return " ".join(w.capitalize() for w in stem.split()) or path.stem


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"['\"`]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def get_git_root(cwd: Path) -> Path | None:
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def is_file_dirty_in_git(path: Path) -> bool:
    try:
        git_root = get_git_root(path.parent)
        if not git_root:
            return False

        if git_root not in GIT_DIRTY_CACHE:
            p = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=str(git_root),
                text=True,
                capture_output=True,
                shell=False
            )
            dirty_set = set()
            if p.returncode == 0:
                for line in p.stdout.splitlines():
                    if len(line) >= 4:
                        raw = line[3:].strip()
                        if " -> " in raw:
                            old, new = raw.split(" -> ", 1)
                            dirty_set.add(old.strip('"'))
                            dirty_set.add(new.strip('"'))
                        else:
                            dirty_set.add(raw.strip('"'))
            GIT_DIRTY_CACHE[git_root] = dirty_set

        rel_path = path.relative_to(git_root).as_posix()
        return rel_path in GIT_DIRTY_CACHE[git_root]
    except Exception:
        return False


def build_git_history_cache(git_root: Path):
    if git_root in GIT_HISTORY_CACHE:
        return
    
    # Query git log name-only for all commits
    p = subprocess.run(
        ["git", "log", "--name-only", "--format=%aI"],
        cwd=str(git_root),
        text=True,
        capture_output=True,
        shell=False
    )
    
    cache: dict[str, tuple[str, str]] = {}
    if p.returncode == 0:
        current_date = None
        for line in p.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # ISO 8601 date match (starts with 4 digits and has T)
            if len(line) >= 19 and line[4] == "-" and line[7] == "-" and "T" in line:
                current_date = line
            elif current_date:
                file_rel = line.strip('"').replace("\\", "/").strip("/")
                if not file_rel:
                    continue
                # The first time we see a file in the log (going from top/newest to bottom/oldest),
                # it's the updated_at time (newest commit date).
                # The last time we see it is the created_at time (oldest commit date).
                if file_rel not in cache:
                    cache[file_rel] = (current_date, current_date)
                else:
                    updated_at = cache[file_rel][1]
                    cache[file_rel] = (current_date, updated_at)
                    
    GIT_HISTORY_CACHE[git_root] = cache


def get_cached_git_timestamps(path: Path) -> tuple[str | None, str | None]:
    try:
        git_root = get_git_root(path.parent)
        if not git_root:
            return None, None
        
        build_git_history_cache(git_root)
        
        rel_path = path.relative_to(git_root).as_posix()
        cache = GIT_HISTORY_CACHE.get(git_root, {})
        if rel_path in cache:
            return cache[rel_path] # (created_at, updated_at)
        return None, None
    except Exception:
        return None, None


def add_missing_frontmatter(text: str, path: Path, required_keys: list[str], defaults: dict, dynamic: dict) -> tuple[str, list[str]]:
    text = normalize_text_for_frontmatter(text)
    fm, body = split_frontmatter(text)
    existing = parse_frontmatter_keys(fm)
    added: list[str] = []

    if fm is None:
        fm_lines: list[str] = []
    else:
        fm_lines = fm.splitlines()

    def add_key(key: str, value: Any):
        nonlocal fm_lines, added
        
        # Check if key is already set (non-empty)
        if key in existing:
            val_str = existing[key].strip("'\" ")
            if val_str and val_str != "[]" and val_str != '""' and val_str != "''":
                # Except for updated_at, which we want to update if dirty
                if key != "updated_at":
                    return
                # If key is updated_at and file is not dirty in git, keep it!
                if not is_file_dirty_in_git(path):
                    return
        
        # Determine value dynamically
        if key == "title":
            value = title_from_filename(path)
        elif key == "slug":
            title_val = existing.get("title", "").strip("'\" ") or title_from_filename(path)
            value = slugify(title_val)
        elif key == "uid":
            value = uuid.uuid4().hex
        elif key == "created_at":
            git_created, _ = get_cached_git_timestamps(path)
            value = git_created
            if not value:
                try:
                    value = datetime.datetime.fromtimestamp(path.stat().st_ctime).astimezone().isoformat(timespec="seconds")
                except Exception:
                    value = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        elif key == "updated_at":
            if is_file_dirty_in_git(path):
                value = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            else:
                _, git_updated = get_cached_git_timestamps(path)
                value = git_updated
                if not value:
                    value = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

        # Find existing line index to replace or append
        line_idx = -1
        for idx, line in enumerate(fm_lines):
            if line.strip().startswith(key + ":"):
                line_idx = idx
                break

        yaml_val = f"{key}: {value_to_yaml(value)}"
        if line_idx != -1:
            # Only update if the value changed
            old_val = fm_lines[line_idx].split(":", 1)[1].strip()
            new_val = value_to_yaml(value)
            if old_val != new_val:
                fm_lines[line_idx] = yaml_val
                added.append(key)
        else:
            fm_lines.append(yaml_val)
            added.append(key)

        existing[key] = value_to_yaml(value)

    for key in required_keys:
        add_key(key, defaults.get(key, ""))

    note_type = existing.get("type", "").strip().strip('"').strip("'")
    for key in dynamic.get(note_type, []):
        add_key(key, defaults.get(key, ""))

    # If any other fields were added/updated, force updated_at to update as well
    if added and "updated_at" in required_keys:
        if "updated_at" not in added:
            now_str = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            line_idx = -1
            for idx, line in enumerate(fm_lines):
                if line.strip().startswith("updated_at:"):
                    line_idx = idx
                    break
            yaml_val = f"updated_at: {value_to_yaml(now_str)}"
            if line_idx != -1:
                fm_lines[line_idx] = yaml_val
            else:
                fm_lines.append(yaml_val)
            added.append("updated_at")

    new_text = "---\n" + "\n".join(fm_lines).rstrip() + "\n---\n\n" + body.lstrip()
    return new_text, added


def get_frontmatter_keys_from_file(path: Path) -> list[str]:
    text = read_text_no_bom(path)
    fm, _body = split_frontmatter(text)
    return list(parse_frontmatter_keys(fm).keys())