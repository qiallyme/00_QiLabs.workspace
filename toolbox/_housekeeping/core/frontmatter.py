from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


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
        if key in existing:
            return
        if key == "title":
            value = title_from_filename(path)
        fm_lines.append(f"{key}: {value_to_yaml(value)}")
        existing[key] = value_to_yaml(value)
        added.append(key)

    for key in required_keys:
        add_key(key, defaults.get(key, ""))

    note_type = existing.get("type", "").strip().strip('"').strip("'")
    for key in dynamic.get(note_type, []):
        add_key(key, defaults.get(key, ""))

    new_text = "---\n" + "\n".join(fm_lines).rstrip() + "\n---\n\n" + body.lstrip()
    return new_text, added


def get_frontmatter_keys_from_file(path: Path) -> list[str]:
    text = read_text_no_bom(path)
    fm, _body = split_frontmatter(text)
    return list(parse_frontmatter_keys(fm).keys())