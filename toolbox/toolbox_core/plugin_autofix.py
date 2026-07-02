from __future__ import annotations

import ast
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .manifest_utils import read_manifest, slugify, titleize_slug, write_manifest
from .plugin_registry import IGNORED_PARTS, infer_category, infer_entry_target, infer_plugin_id, manifest_path_for, tools_root


@dataclass
class AutoFixAction:
    code: str
    path: str
    message: str
    applied: bool = False


STDLIB_ALLOWLIST = {
    "argparse",
    "ast",
    "csv",
    "datetime",
    "functools",
    "glob",
    "hashlib",
    "importlib",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "queue",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "threading",
    "time",
    "tkinter",
    "traceback",
    "typing",
    "urllib",
    "webbrowser",
}


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def candidate_plugin_dirs(root: Path) -> list[Path]:
    base = tools_root(root)
    if not base.exists():
        return []
    dirs: set[Path] = set()
    for path in base.glob("*/*"):
        if path.is_dir() and not _ignored(path):
            dirs.add(path)
    return sorted(dirs)


def detect_requirements(plugin_dir: Path) -> list[str]:
    modules: set[str] = set()
    for py_file in sorted(plugin_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".", 1)[0])
    local_modules = {p.stem for p in plugin_dir.glob("*.py")}
    detected = sorted(m for m in modules if m not in STDLIB_ALLOWLIST and m not in local_modules and not m.startswith("_"))
    return detected


def _backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak-{stamp}")
    shutil.copy2(path, backup)
    return backup


def basic_manifest(plugin_dir: Path, root: Path) -> dict[str, Any]:
    target = infer_entry_target(plugin_dir)
    suffix = Path(target).suffix.lower()
    entry_type = "script"
    if suffix == ".bat":
        entry_type = "bat"
    elif suffix == ".exe":
        entry_type = "exe"
    return {
        "plugin_id": infer_plugin_id(plugin_dir, root),
        "tool_id": infer_plugin_id(plugin_dir, root),
        "name": titleize_slug(plugin_dir.name),
        "category": infer_category(plugin_dir, root),
        "version": "0.1.0",
        "enabled": True,
        "description": f"{titleize_slug(plugin_dir.name)} plugin.",
        "entry": {
            "type": entry_type,
            "target": target,
            "class_name": "",
        },
        "requirements": [],
    }


def patch_existing_manifest(existing: dict[str, Any], plugin_dir: Path, root: Path) -> tuple[dict[str, Any], bool]:
    patched = dict(existing)
    changed = False

    if not patched.get("tool_id") and not patched.get("plugin_id"):
        patched["plugin_id"] = infer_plugin_id(plugin_dir, root)
        patched["tool_id"] = patched["plugin_id"]
        changed = True
    if not patched.get("name"):
        patched["name"] = titleize_slug(plugin_dir.name)
        changed = True
    if not patched.get("category"):
        patched["category"] = infer_category(plugin_dir, root)
        changed = True
    if not patched.get("description"):
        patched["description"] = f"{patched.get('name') or titleize_slug(plugin_dir.name)} plugin."
        changed = True
    if "enabled" not in patched:
        patched["enabled"] = True
        changed = True
    if not patched.get("entry") and not patched.get("launch"):
        target = infer_entry_target(plugin_dir)
        patched["entry"] = {
            "type": "bat" if Path(target).suffix.lower() == ".bat" else "exe" if Path(target).suffix.lower() == ".exe" else "script",
            "target": target,
            "class_name": "",
        }
        changed = True

    return patched, changed


def autofix_plugin(plugin_dir: Path, root: Path, apply: bool = False) -> list[AutoFixAction]:
    actions: list[AutoFixAction] = []
    manifest_path = manifest_path_for(plugin_dir) or (plugin_dir / "manifest.yaml")
    existing = read_manifest(manifest_path) if manifest_path.exists() else {}
    normalized = basic_manifest(plugin_dir, root) if not existing else {}
    detected = detect_requirements(plugin_dir)

    if not manifest_path.exists():
        actions.append(AutoFixAction("create_manifest", str(manifest_path), "Create a basic manifest from folder path and detected entry.", apply))
        if apply:
            write_manifest(manifest_path, normalized)
    else:
        patched, needs_update = patch_existing_manifest(existing, plugin_dir, root)
        if needs_update:
            actions.append(AutoFixAction("update_manifest", str(manifest_path), "Fill safe missing manifest fields.", apply))
            if apply:
                _backup(manifest_path)
                write_manifest(manifest_path, patched)

    readme = plugin_dir / "README.md"
    if not readme.exists():
        actions.append(AutoFixAction("create_readme", str(readme), "Create README.md.", apply))
        if apply:
            title = existing.get("name") or normalized.get("name") or titleize_slug(plugin_dir.name)
            description = existing.get("description") or normalized.get("description") or f"{title} plugin."
            readme.write_text(f"# {title}\n\n{description}\n", encoding="utf-8")

    init = plugin_dir / "__init__.py"
    if not init.exists():
        actions.append(AutoFixAction("create_init", str(init), "Create __init__.py.", apply))
        if apply:
            init.write_text("", encoding="utf-8")

    if detected:
        detected_path = plugin_dir / "requirements.detected.txt"
        actions.append(AutoFixAction("write_detected_requirements", str(detected_path), "Write detected Python imports.", apply))
        if apply:
            detected_path.write_text("\n".join(detected) + "\n", encoding="utf-8")

    return actions


def autofix_all(root: Path, apply: bool = False) -> dict[str, Any]:
    actions: list[AutoFixAction] = []
    for plugin_dir in candidate_plugin_dirs(root):
        actions.extend(autofix_plugin(plugin_dir, root, apply=apply))
    report = {
        "mode": "apply" if apply else "preview",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "actions": [asdict(action) for action in actions],
    }
    out = root / "toolbox_autofix_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
