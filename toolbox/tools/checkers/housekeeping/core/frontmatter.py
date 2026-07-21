from __future__ import annotations

import re
import io
import uuid
import datetime
import subprocess
from pathlib import Path
from typing import Any
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
GIT_DIRTY_CACHE: dict[Path, set[str]] = {}
GIT_HISTORY_CACHE: dict[Path, dict[str, tuple[str, str]]] = {}

def normalize_text_for_frontmatter(text: str) -> str:
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

def parse_frontmatter_keys(fm: str | None) -> dict[str, Any]:
    if not fm or not fm.strip():
        return {}
    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        data = yaml.load(fm)
        return dict(data) if data else {}
    except MarkedYAMLError:
        return {}

def title_from_filename(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[_-]?", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    return " ".join(w.capitalize() for w in stem.split()) or path.stem

def infer_note_type(path: Path, existing: dict[str, Any]) -> str:
    current = str(existing.get("type", "")).strip().strip('"').strip("'")
    if current and current != "None":
        return current
    if path.name.lower() in {"_index.md", "index.md"}:
        return "index"
    has_date = bool(str(existing.get("date", "")).strip().strip('"').strip("'"))
    event_markers = ("event_type", "category", "involved", "severity", "critical")
    if has_date and any(key in existing for key in event_markers):
        return "event"
    return "note"

def slugify(value: str) -> str:
    value = str(value).lower()
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
            if len(line) >= 19 and line[4] == "-" and line[7] == "-" and "T" in line:
                current_date = line
            elif current_date:
                file_rel = line.strip('"').replace("\\", "/").strip("/")
                if not file_rel:
                    continue
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
            return cache[rel_path]
        return None, None
    except Exception:
        return None, None

def add_missing_frontmatter(text: str, path: Path, required_keys: list[str], defaults: dict, dynamic: dict) -> tuple[str, list[str]]:
    text = normalize_text_for_frontmatter(text)
    fm, body = split_frontmatter(text)
    added: list[str] = []

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        data = yaml.load(fm) if fm and fm.strip() else yaml.map()
    except MarkedYAMLError:
        # If parsing fails due to duplicates, we can attempt to load without duplicate checks
        # But ruamel handles strict duplication by raising. We can instantiate a new parser
        yaml_lax = YAML(typ='safe')
        try:
            data = yaml_lax.load(fm) or {}
            # Convert to roundtrip CommentedMap
            data = yaml.load(yaml.dump(data) or "") if data else yaml.map()
        except Exception:
            data = yaml.map()

    if data is None:
        data = yaml.map()

    # Determine dynamic values first
    title_val = str(data.get("title", "")) or title_from_filename(path)
    type_val = infer_note_type(path, dict(data))

    def _val_empty(v: Any) -> bool:
        if v is None: return True
        if isinstance(v, list) and not v: return True
        if isinstance(v, str) and not v.strip(): return True
        return False

    def process_key(key: str, default_val: Any):
        nonlocal data, added
        val = data.get(key)
        
        # Don't overwrite existing non-empty values (except updated_at context)
        if not _val_empty(val) and key != "updated_at":
            return
            
        if key == "updated_at" and not _val_empty(val) and not is_file_dirty_in_git(path):
            return

        new_val = default_val
        if key == "title": new_val = title_val
        elif key == "type": new_val = type_val
        elif key == "slug": new_val = slugify(title_val)
        elif key == "uid": new_val = uuid.uuid4().hex
        elif key == "created_at":
            git_created, _ = get_cached_git_timestamps(path)
            new_val = git_created
            if not new_val:
                try:
                    new_val = datetime.datetime.fromtimestamp(path.stat().st_ctime).astimezone().isoformat(timespec="seconds")
                except Exception:
                    new_val = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        elif key == "updated_at":
            if is_file_dirty_in_git(path):
                new_val = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            else:
                _, git_updated = get_cached_git_timestamps(path)
                new_val = git_updated
                if not new_val:
                    new_val = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        
        # Enforce list types
        if isinstance(default_val, list) and not isinstance(new_val, list):
            new_val = [new_val] if new_val and not _val_empty(new_val) else []

        if val != new_val:
            data[key] = new_val
            added.append(key)

    # 1. Process required keys in order to enforce master template order
    ordered_data = yaml.map()
    for key in required_keys:
        process_key(key, defaults.get(key, ""))
        if key in data:
            ordered_data[key] = data[key]

    # 2. Process dynamic keys based on type
    for key in dynamic.get(type_val, []):
        process_key(key, defaults.get(key, ""))
        if key in data:
            ordered_data[key] = data[key]

    # 3. Add any existing unknown keys back at the bottom
    for key in data:
        if key not in ordered_data:
            ordered_data[key] = data[key]

    # Update updated_at if anything else changed
    if added and "updated_at" in required_keys and "updated_at" not in added:
        now_str = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        ordered_data["updated_at"] = now_str
        added.append("updated_at")

    # Dump the ordered YAML
    out_io = io.StringIO()
    yaml.dump(ordered_data, out_io)
    fm_out = out_io.getvalue().strip()

    # Never insert markdown into frontmatter (validate that no "---\n" occurs inside the dump somehow)
    fm_out = fm_out.replace("---\n", "")

    new_text = f"---\n{fm_out}\n---\n\n{body.lstrip()}"
    
    # Final Validation
    try:
        yaml.load(fm_out)
    except MarkedYAMLError as e:
        raise ValueError(f"Failed to validate generated YAML for {path.name}: {e}")

    return new_text, added

def get_frontmatter_keys_from_file(path: Path) -> list[str]:
    text = read_text_no_bom(path)
    fm, _body = split_frontmatter(text)
    return list(parse_frontmatter_keys(fm).keys())

