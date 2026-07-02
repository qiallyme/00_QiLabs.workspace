from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .manifest_utils import read_manifest, write_manifest, slugify, titleize_slug


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str
    fixable: bool = False
    fixed: bool = False


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def infer_category(tool_dir: Path, tools_root: Path) -> str:
    try:
        rel = tool_dir.relative_to(tools_root)
        parts = rel.parts
        return parts[0] if len(parts) >= 2 else 'uncategorized'
    except ValueError:
        return 'uncategorized'


def infer_tool_slug(tool_dir: Path) -> str:
    return slugify(tool_dir.name)


def infer_tool_id(tool_dir: Path, tools_root: Path) -> str:
    category = slugify(infer_category(tool_dir, tools_root)).replace('_', '.')
    slug = infer_tool_slug(tool_dir).replace('_', '.')
    return f'{category}.{slug}'


def infer_launch_target(tool_dir: Path) -> str | None:
    preferred = tool_dir / f'{tool_dir.name}.py'
    if preferred.exists():
        return preferred.name
    py_files = sorted(p for p in tool_dir.glob('*.py') if p.name != '__init__.py')
    if py_files:
        return py_files[0].name
    bat_files = sorted(tool_dir.glob('*.bat'))
    if bat_files:
        return bat_files[0].name
    ps1_files = sorted(tool_dir.glob('*.ps1'))
    if ps1_files:
        return ps1_files[0].name
    return None


def infer_launch_type(target: str | None) -> str:
    if not target:
        return 'manual'
    suffix = Path(target).suffix.lower()
    if suffix == '.py':
        return 'python'
    if suffix == '.bat':
        return 'bat'
    if suffix == '.ps1':
        return 'powershell'
    return 'file'


def normalize_manifest(tool_dir: Path, tools_root: Path, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    category = existing.get('category') or infer_category(tool_dir, tools_root)
    tool_id = existing.get('tool_id') or infer_tool_id(tool_dir, tools_root)
    name = existing.get('name') or titleize_slug(tool_dir.name)
    target = None
    launch = existing.get('launch') if isinstance(existing.get('launch'), dict) else {}
    if launch:
        target = launch.get('target')
    target = target or infer_launch_target(tool_dir)

    normalized = {
        'tool_id': tool_id,
        'name': name,
        'category': category,
        'version': str(existing.get('version') or '0.1.0'),
        'enabled': bool(existing.get('enabled', True)),
        'description': existing.get('description') or f'{name} tool.',
        'tags': existing.get('tags') if isinstance(existing.get('tags'), list) else [category, slugify(tool_dir.name)],
        'launch': {
            'type': launch.get('type') or infer_launch_type(target),
            'target': target or '',
            'working_dir': launch.get('working_dir') or '.',
            'open_console': bool(launch.get('open_console', True)),
        },
        'conflicts': existing.get('conflicts') if isinstance(existing.get('conflicts'), list) else [],
    }
    # Preserve extra keys.
    for key, value in existing.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def find_tool_dirs(tools_root: Path) -> list[Path]:
    if not tools_root.exists():
        return []
    dirs: list[Path] = []
    for manifest in sorted(list(tools_root.rglob('manifest.yaml')) + list(tools_root.rglob('manifest.json'))):
        if '_pending' in manifest.parts or '__pycache__' in manifest.parts:
            continue
        dirs.append(manifest.parent)
    return sorted(set(dirs))


def validate_tool(tool_dir: Path, tools_root: Path, seen_ids: set[str] | None = None) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    seen_ids = seen_ids if seen_ids is not None else set()
    manifest_path = tool_dir / 'manifest.yaml'
    if not manifest_path.exists():
        manifest_path = tool_dir / 'manifest.json'

    data = read_manifest(manifest_path) if manifest_path.exists() else {}
    manifest_rel = str(manifest_path.relative_to(tools_root.parent)) if manifest_path.exists() else str(tool_dir)

    if not manifest_path.exists():
        findings.append(Finding('ERROR', 'missing_manifest', str(tool_dir), 'Missing manifest.yaml or manifest.json.', True))
        data = normalize_manifest(tool_dir, tools_root, {})
    if not data.get('tool_id'):
        findings.append(Finding('ERROR', 'missing_tool_id', manifest_rel, 'Missing required tool_id.', True))
    else:
        if data['tool_id'] in seen_ids:
            findings.append(Finding('ERROR', 'duplicate_tool_id', manifest_rel, f'Duplicate tool_id: {data["tool_id"]}', False))
        seen_ids.add(data['tool_id'])
    if not data.get('name'):
        findings.append(Finding('ERROR', 'missing_name', manifest_rel, 'Missing required name.', True))
    if not data.get('category'):
        findings.append(Finding('ERROR', 'missing_category', manifest_rel, 'Missing required category.', True))

    launch = data.get('launch') if isinstance(data.get('launch'), dict) else {}
    target = launch.get('target') if launch else None
    if not target:
        findings.append(Finding('ERROR', 'missing_launch_target', manifest_rel, 'Missing launch.target.', True))
    else:
        target_path = tool_dir / str(target)
        if not target_path.exists():
            findings.append(Finding('ERROR', 'missing_entrypoint', manifest_rel, f'Launch target does not exist: {target}', True))

    if not (tool_dir / 'README.md').exists():
        findings.append(Finding('WARNING', 'missing_readme', str(tool_dir.relative_to(tools_root.parent)), 'Missing README.md.', True))
    if not (tool_dir / '__init__.py').exists():
        findings.append(Finding('WARNING', 'missing_init', str(tool_dir.relative_to(tools_root.parent)), 'Missing __init__.py.', True))

    return data, findings


def validate_all(toolbox_root: Path) -> dict[str, Any]:
    tools_root = toolbox_root / 'tools'
    seen: set[str] = set()
    active: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for tool_dir in find_tool_dirs(tools_root):
        data, local = validate_tool(tool_dir, tools_root, seen)
        findings.extend(local)
        if data.get('enabled', True) and not any(f.severity == 'ERROR' for f in local):
            active.append({'tool_id': data.get('tool_id'), 'name': data.get('name'), 'category': data.get('category'), 'path': str(tool_dir)})
    return {
        'active_tools': active,
        'errors': sum(1 for f in findings if f.severity == 'ERROR'),
        'warnings': sum(1 for f in findings if f.severity == 'WARNING'),
        'findings': [asdict(f) for f in findings],
    }


def autofix_tool(tool_dir: Path, tools_root: Path, dry_run: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    manifest_path = tool_dir / 'manifest.yaml'
    if not manifest_path.exists() and (tool_dir / 'manifest.json').exists():
        manifest_path = tool_dir / 'manifest.json'
    existing = read_manifest(manifest_path) if manifest_path.exists() else {}
    normalized = normalize_manifest(tool_dir, tools_root, existing)

    before_hash = sha256(manifest_path)
    if not dry_run:
        write_manifest(manifest_path if manifest_path.suffix else tool_dir / 'manifest.yaml', normalized)
    findings.append(Finding('INFO', 'manifest_normalized', str(manifest_path), 'Manifest normalized with inferred missing fields.', True, not dry_run))

    readme = tool_dir / 'README.md'
    if not readme.exists():
        content = f"# {normalized['name']}\n\n{normalized['description']}\n\n## Launch\n\nThis tool is discovered by QiLabs Toolbox Manager through `manifest.yaml`.\n"
        if not dry_run:
            readme.write_text(content, encoding='utf-8')
        findings.append(Finding('INFO', 'readme_created', str(readme), 'README.md created.', True, not dry_run))

    init = tool_dir / '__init__.py'
    if not init.exists():
        if not dry_run:
            init.write_text('', encoding='utf-8')
        findings.append(Finding('INFO', 'init_created', str(init), '__init__.py created.', True, not dry_run))

    # Ensure there is at least one runnable target if possible.
    target = normalized.get('launch', {}).get('target')
    if target and not (tool_dir / target).exists() and normalized.get('launch', {}).get('type') == 'python':
        stub = tool_dir / target
        content = """from __future__ import annotations\n\n\ndef main() -> None:\n    print('Tool stub created by QiLabs Toolbox Manager. Replace this body with your tool logic.')\n\n\nif __name__ == '__main__':\n    main()\n"""
        if not dry_run:
            stub.write_text(content, encoding='utf-8')
        findings.append(Finding('INFO', 'stub_created', str(stub), 'Missing Python target stub created.', True, not dry_run))

    return findings


def autofix_all(toolbox_root: Path, dry_run: bool = True) -> dict[str, Any]:
    tools_root = toolbox_root / 'tools'
    all_findings: list[Finding] = []
    for tool_dir in find_tool_dirs(tools_root):
        all_findings.extend(autofix_tool(tool_dir, tools_root, dry_run=dry_run))
    report = {
        'mode': 'dry_run' if dry_run else 'apply',
        'findings': [asdict(f) for f in all_findings],
    }
    out = toolbox_root / 'toolbox_autofix_report.json'
    if not dry_run:
        out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def validation_report_markdown(result: dict[str, Any]) -> str:
    lines = ['# Toolbox Validation Report', '']
    lines.append(f"- Active tools: {len(result.get('active_tools', []))}")
    lines.append(f"- Errors: {result.get('errors', 0)}")
    lines.append(f"- Warnings: {result.get('warnings', 0)}")
    lines.append(f"- Findings: {len(result.get('findings', []))}")
    lines.append('')
    lines.append('## Active Tools')
    lines.append('')
    for tool in result.get('active_tools', []):
        lines.append(f"- `{tool.get('tool_id')}` — {tool.get('name')} ({tool.get('category')})")
    if not result.get('active_tools'):
        lines.append('- None')
    lines.append('')
    lines.append('## Findings')
    lines.append('')
    for f in result.get('findings', []):
        lines.append(f"- **{f['severity']}** `{f['code']}` — {f['message']}")
        lines.append(f"  - Path: `{f['path']}`")
        if f.get('fixable'):
            lines.append('  - Fixable: yes')
    return '\n'.join(lines) + '\n'
