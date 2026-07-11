from __future__ import annotations

import re
from pathlib import Path

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[_\-\s]+")


def slugify_name(stem: str, word_separator: str = "-") -> str:
    stem = stem.strip()
    m = DATE_PREFIX_RE.match(stem)
    date = ""
    if m:
        date = m.group(1)
        stem = stem[m.end():]

    stem = stem.replace("&", " and ")
    stem = re.sub(r"[^A-Za-z0-9]+", word_separator, stem)
    stem = re.sub(re.escape(word_separator) + r"{2,}", word_separator, stem)
    stem = stem.strip(word_separator).lower()

    if date:
        return f"{date}_{stem}" if stem else date
    return stem or "untitled"


def normalized_markdown_filename(path: Path, config: dict) -> str:
    rules = config.get("filename_rules", {})
    preserve = set(rules.get("preserve", []))
    if path.name in preserve:
        return path.name
    new_stem = slugify_name(path.stem, rules.get("word_separator", "-"))
    return new_stem + path.suffix.lower()


def should_consider_for_rename(path: Path, config: dict) -> bool:
    rules = config.get("filename_rules", {})
    if path.name in set(rules.get("preserve", [])):
        return False
    if rules.get("markdown_only", True) and path.suffix.lower() != ".md":
        return False
    return True
