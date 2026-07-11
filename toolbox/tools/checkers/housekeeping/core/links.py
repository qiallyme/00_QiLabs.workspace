from __future__ import annotations

import re
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]+)?(\|[^\]]+)?\]\]")


def build_stem_rename_map(rename_map: dict[str, str]) -> dict[str, str]:
    out = {}
    for old, new in rename_map.items():
        old_stem = Path(old).stem
        new_stem = Path(new).stem
        out[old_stem] = new_stem
    return out


def rewrite_wikilinks(text: str, rename_map: dict[str, str]) -> tuple[str, int]:
    stem_map = build_stem_rename_map(rename_map)
    count = 0

    def repl(match):
        nonlocal count
        target = match.group(1)
        heading = match.group(2) or ""
        alias = match.group(3) or ""
        target_stem = Path(target).stem
        if target_stem in stem_map:
            count += 1
            return f"[[{stem_map[target_stem]}{heading}{alias}]]"
        return match.group(0)

    return WIKILINK_RE.sub(repl, text), count


def rewrite_markdown_links(text: str, rename_map: dict[str, str]) -> tuple[str, int]:
    count = 0
    for old, new in rename_map.items():
        old_name = Path(old).name
        new_name = Path(new).name
        old_enc = old_name.replace(" ", "%20")
        new_enc = new_name.replace(" ", "%20")
        for needle, replacement in [(old_name, new_name), (old_enc, new_enc)]:
            if needle in text:
                text = text.replace(needle, replacement)
                count += 1
    return text, count
