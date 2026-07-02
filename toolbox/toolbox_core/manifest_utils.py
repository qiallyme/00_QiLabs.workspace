from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    out = []
    last_dash = False
    for ch in value.strip().lower():
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif ch in {' ', '-', '_', '.', '/'}:
            if not last_dash:
                out.append('_')
                last_dash = True
    return ''.join(out).strip('_') or 'new_tool'


def titleize_slug(value: str) -> str:
    return ' '.join(part.capitalize() for part in value.replace('-', '_').split('_') if part) or 'New Tool'


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == '':
        return ''
    if raw.lower() == 'true':
        return True
    if raw.lower() == 'false':
        return False
    if raw.lower() in {'null', 'none'}:
        return None
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    return raw


def read_manifest(path: Path) -> dict[str, Any]:
    """Read simple manifest.yaml/manifest.json. Supports the QiLabs simple YAML shape."""
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8', errors='replace')
    if path.suffix.lower() == '.json':
        return json.loads(text)

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    last_key_at_indent: dict[int, str] = {}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith('- '):
            value = _parse_scalar(stripped[2:])
            if not isinstance(parent, list):
                # This parser is intentionally conservative. Old manifests rarely use complex lists.
                continue
            parent.append(value)
            continue

        if ':' not in stripped:
            continue

        key, raw_value = stripped.split(':', 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value == '':
            # Decide list vs dict by peeking at next meaningful line.
            next_is_list = False
            for j in range(i, len(lines)):
                nxt = lines[j].strip()
                if not nxt or nxt.startswith('#'):
                    continue
                next_indent = len(lines[j]) - len(lines[j].lstrip(' '))
                next_is_list = next_indent > indent and nxt.startswith('- ')
                break
            value: Any = [] if next_is_list else {}
        else:
            value = _parse_scalar(raw_value)

        if isinstance(parent, dict):
            parent[key] = value
            last_key_at_indent[indent] = key
            if isinstance(value, (dict, list)):
                stack.append((indent, value))

    return root


def _quote(value: str) -> str:
    if value == '' or value.lower() in {'true', 'false', 'null'} or any(ch in value for ch in [':', '#', '{', '}', '[', ']', ',']):
        return json.dumps(value)
    return value


def yaml_dump(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    pad = ' ' * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f'{pad}{key}:')
            lines.append(yaml_dump(value, indent + 2).rstrip())
        elif isinstance(value, list):
            lines.append(f'{pad}{key}:')
            for item in value:
                if isinstance(item, dict):
                    lines.append(f'{pad}  -')
                    lines.append(yaml_dump(item, indent + 4).rstrip())
                else:
                    if isinstance(item, str):
                        item_out = _quote(item)
                    else:
                        item_out = json.dumps(item)
                    lines.append(f'{pad}  - {item_out}')
        elif isinstance(value, bool):
            lines.append(f'{pad}{key}: {str(value).lower()}')
        elif value is None:
            lines.append(f'{pad}{key}: null')
        elif isinstance(value, str):
            lines.append(f'{pad}{key}: {_quote(value)}')
        else:
            lines.append(f'{pad}{key}: {value}')
    return '\n'.join(lines) + '\n'


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == '.json':
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    else:
        path.write_text(yaml_dump(data), encoding='utf-8')
