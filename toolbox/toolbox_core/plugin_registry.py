from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .manifest_utils import read_manifest, slugify, titleize_slug

IGNORED_PARTS = {
    "_pending",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "archives",
    "_archive",
    "_cleanup_archive",
}

BASETOOL_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*BaseTool[^)]*)\)\s*:")
PLUGIN_V2_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*:[\s\S]*?def\s+build_view\s*\(")
PACKAGE_NAME_MAP = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "send2trash": "Send2Trash",
}
IMPORT_NAME_MAP = {
    "pillow": "PIL",
    "pyyaml": "yaml",
    "Send2Trash": "send2trash",
}
LOCAL_OR_STDLIB_REQUIREMENTS = {
    "core", "toolbox_core", "python_stdlib", "decimal", "concurrent",
    "dataclasses", "tkinter", "pathlib", "typing", "csv", "json",
}


@dataclass
class RegistryFinding:
    severity: str
    code: str
    path: str
    message: str
    plugin_id: str = ""
    fixable: bool = False


def tools_root(toolbox_root: Path) -> Path:
    return toolbox_root / "tools"


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def manifest_path_for(plugin_dir: Path) -> Path | None:
    for name in ("manifest.yaml", "manifest.json"):
        path = plugin_dir / name
        if path.exists():
            return path
    return None


def find_plugin_dirs(root: Path) -> list[Path]:
    base = tools_root(root)
    if not base.exists():
        return []
    dirs: set[Path] = set()
    for manifest in sorted(list(base.rglob("manifest.yaml")) + list(base.rglob("manifest.json"))):
        if is_ignored(manifest):
            continue
        try:
            rel_parts = manifest.parent.relative_to(base).parts
        except ValueError:
            continue
        if len(rel_parts) < 2:
            continue
        dirs.add(manifest.parent)
    return sorted(dirs)


def infer_category(plugin_dir: Path, root: Path) -> str:
    try:
        rel = plugin_dir.relative_to(tools_root(root))
        return slugify(rel.parts[0]) if rel.parts else "uncategorized"
    except ValueError:
        return "uncategorized"


def infer_plugin_id(plugin_dir: Path, root: Path) -> str:
    return f"{infer_category(plugin_dir, root)}.{slugify(plugin_dir.name)}"


def infer_entry_target(plugin_dir: Path) -> str:
    preferred = plugin_dir / f"{plugin_dir.name}.py"
    if preferred.exists():
        return preferred.name
    for pattern in ("*.py", "*.bat", "*.exe", "*.ps1"):
        for candidate in sorted(plugin_dir.glob(pattern)):
            if candidate.name != "__init__.py":
                return candidate.name
    return ""


def infer_entry_type(target: str, data: dict[str, Any] | None = None) -> str:
    data = data or {}
    explicit = str(data.get("type") or "").lower()
    if explicit in {"plugin_v2", "legacy_basetool", "script", "bat", "exe"}:
        return explicit
    suffix = Path(target).suffix.lower()
    if suffix == ".bat":
        return "bat"
    if suffix == ".exe":
        return "exe"
    return "script"


def detect_basetool_class(plugin_dir: Path, target: str) -> str:
    path = plugin_dir / target
    if not path.exists() or path.suffix.lower() != ".py":
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = BASETOOL_RE.search(text)
    return match.group(1) if match else ""


def detect_plugin_v2_class(plugin_dir: Path, target: str) -> str:
    path = plugin_dir / target
    if not path.exists() or path.suffix.lower() != ".py":
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = PLUGIN_V2_RE.search(text)
    return match.group(1) if match else ""


def normalize_entry(data: dict[str, Any], plugin_dir: Path) -> dict[str, Any]:
    entry = data.get("entry") if isinstance(data.get("entry"), dict) else {}
    launch = data.get("launch") if isinstance(data.get("launch"), dict) else {}
    module = data.get("module") if isinstance(data.get("module"), dict) else {}

    target = str(entry.get("target") or launch.get("target") or module.get("file") or infer_entry_target(plugin_dir))
    class_name = str(entry.get("class_name") or data.get("class_name") or module.get("class_name") or module.get("entrypoint") or "")
    if class_name.upper() == "UNKNOWN":
        class_name = ""
    entry_type = infer_entry_type(target, entry or launch)

    launch_type = str(launch.get("type") or "").lower()
    if entry_type == "script" and class_name:
        if launch_type in {"native_class", "legacy_basetool"} or module.get("class_name") or module.get("entrypoint"):
            entry_type = "legacy_basetool"
        elif data.get("plugin_id") or data.get("entry"):
            entry_type = str(entry.get("type") or "plugin_v2").lower()

    if entry_type == "script" and not class_name:
        detected_native = detect_plugin_v2_class(plugin_dir, target)
        if detected_native:
            class_name = detected_native
            entry_type = "plugin_v2"

    if entry_type == "script" and not class_name:
        detected_class = detect_basetool_class(plugin_dir, target)
        if detected_class:
            class_name = detected_class
            entry_type = "legacy_basetool"

    return {
        "type": entry_type,
        "target": target,
        "class_name": class_name,
        "working_dir": str(entry.get("working_dir") or launch.get("working_dir") or "."),
        "open_console": bool(entry.get("open_console", launch.get("open_console", False))),
    }


def normalize_manifest(data: dict[str, Any], plugin_dir: Path, root: Path) -> dict[str, Any]:
    plugin_id = str(data.get("plugin_id") or data.get("tool_id") or infer_plugin_id(plugin_dir, root))
    category = str(data.get("category") or infer_category(plugin_dir, root))
    name = str(data.get("name") or titleize_slug(plugin_dir.name))
    requirements = data.get("requirements") if isinstance(data.get("requirements"), list) else []
    detected_path = plugin_dir / "requirements.detected.txt"
    if detected_path.exists():
        detected = [
            line.strip()
            for line in detected_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        requirements = sorted(set([str(item) for item in requirements] + [PACKAGE_NAME_MAP.get(item, item) for item in detected]))
    return {
        "plugin_id": plugin_id,
        "tool_id": str(data.get("tool_id") or plugin_id),
        "name": name,
        "category": category,
        "description": str(data.get("description") or f"{name} plugin."),
        "version": str(data.get("version") or "0.1.0"),
        "enabled": bool(data.get("enabled", True)),
        "requirements": [str(item) for item in requirements],
        "entry": normalize_entry(data, plugin_dir),
        "actions": data.get("actions") if isinstance(data.get("actions"), list) else [],
        "raw": data,
    }


def requirement_available(requirement: str) -> bool:
    package = requirement.strip()
    if not package:
        return True
    if package in LOCAL_OR_STDLIB_REQUIREMENTS:
        return True
    for sep in ("==", ">=", "<=", "~=", ">", "<", "["):
        package = package.split(sep, 1)[0]
    package = package.strip()
    if not package:
        return True
    import_name = IMPORT_NAME_MAP.get(package, package).replace("-", "_")
    return importlib.util.find_spec(import_name) is not None


def validate_plugin_record(record: dict[str, Any], root: Path, seen: set[str]) -> list[RegistryFinding]:
    findings: list[RegistryFinding] = []
    plugin_id = record.get("plugin_id") or ""
    manifest_path = root / record.get("manifest_path", "")
    plugin_dir = root / record.get("path", "")
    entry = record.get("entry") or {}

    if not plugin_id:
        findings.append(RegistryFinding("ERROR", "missing_plugin_id", str(manifest_path), "Missing plugin_id/tool_id.", fixable=True))
    elif plugin_id in seen:
        findings.append(RegistryFinding("ERROR", "duplicate_plugin_id", str(manifest_path), f"Duplicate plugin id: {plugin_id}", plugin_id))
    seen.add(plugin_id)

    for field in ("name", "category", "description"):
        if not record.get(field):
            findings.append(RegistryFinding("ERROR", f"missing_{field}", str(manifest_path), f"Missing {field}.", plugin_id, True))

    target = str(entry.get("target") or "")
    if not target:
        findings.append(RegistryFinding("ERROR", "missing_entry_target", str(manifest_path), "Missing entry.target or launch.target.", plugin_id, True))
    elif not (plugin_dir / target).exists():
        findings.append(RegistryFinding("ERROR", "missing_entry_file", str(manifest_path), f"Entry target does not exist: {target}", plugin_id, True))

    entry_type = str(entry.get("type") or "")
    if entry_type not in {"plugin_v2", "legacy_basetool", "script", "bat", "exe"}:
        findings.append(RegistryFinding("ERROR", "invalid_entry_type", str(manifest_path), f"Unsupported entry type: {entry_type}", plugin_id, True))

    if entry_type in {"plugin_v2", "legacy_basetool"} and not entry.get("class_name"):
        findings.append(RegistryFinding("WARNING", "missing_class_name", str(manifest_path), "Class-based plugin has no class_name.", plugin_id, True))

    if not (plugin_dir / "README.md").exists():
        findings.append(RegistryFinding("WARNING", "missing_readme", str(plugin_dir), "Missing README.md.", plugin_id, True))
    if not (plugin_dir / "__init__.py").exists():
        findings.append(RegistryFinding("WARNING", "missing_init", str(plugin_dir), "Missing __init__.py.", plugin_id, True))

    for requirement in record.get("requirements", []):
        if not requirement_available(requirement):
            findings.append(RegistryFinding("WARNING", "missing_requirement", str(manifest_path), f"Requirement may be missing: {requirement}", plugin_id, True))

    return findings


def build_registry(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    findings: list[RegistryFinding] = []
    seen: set[str] = set()

    for plugin_dir in find_plugin_dirs(root):
        manifest_path = manifest_path_for(plugin_dir)
        if manifest_path is None:
            continue
        try:
            raw = read_manifest(manifest_path)
            record = normalize_manifest(raw, plugin_dir, root)
            record["path"] = str(plugin_dir.relative_to(root)).replace("\\", "/")
            record["manifest_path"] = str(manifest_path.relative_to(root)).replace("\\", "/")
            local_findings = validate_plugin_record(record, root, seen)
            findings.extend(local_findings)
            if record.get("enabled", True):
                records.append(record)
        except Exception as exc:
            rel = str(manifest_path.relative_to(root)).replace("\\", "/")
            findings.append(RegistryFinding("ERROR", "manifest_load_failed", rel, f"Could not read manifest: {exc}"))

    return {
        "schema": "qilabs.toolbox.registry.v2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "toolbox_root": str(root),
        "plugin_count": len(records),
        "plugins": sorted(records, key=lambda item: (item.get("category", ""), item.get("name", ""))),
        "tools": sorted(records, key=lambda item: (item.get("category", ""), item.get("name", ""))),
        "findings": [asdict(finding) for finding in findings],
        "errors": sum(1 for finding in findings if finding.severity == "ERROR"),
        "warnings": sum(1 for finding in findings if finding.severity == "WARNING"),
    }


def validation_report_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# QiLabs Toolbox Validation Report",
        "",
        f"- Generated: {registry.get('generated_at', '')}",
        f"- Plugins: {registry.get('plugin_count', 0)}",
        f"- Errors: {registry.get('errors', 0)}",
        f"- Warnings: {registry.get('warnings', 0)}",
        "",
        "## Plugins",
        "",
    ]
    for plugin in registry.get("plugins", []):
        lines.append(f"- `{plugin.get('plugin_id')}` - {plugin.get('name')} ({plugin.get('category')})")
    if not registry.get("plugins"):
        lines.append("- None")
    lines.extend(["", "## Findings", ""])
    for finding in registry.get("findings", []):
        lines.append(f"- **{finding.get('severity')}** `{finding.get('code')}` - {finding.get('message')}")
        lines.append(f"  - Path: `{finding.get('path')}`")
        if finding.get("plugin_id"):
            lines.append(f"  - Plugin: `{finding.get('plugin_id')}`")
        if finding.get("fixable"):
            lines.append("  - Fixable: yes")
    if not registry.get("findings"):
        lines.append("- No findings.")
    return "\n".join(lines) + "\n"


def save_registry(root: Path) -> Path:
    registry = build_registry(root)
    out = root / "toolbox_registry.json"
    out.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    report = root / "toolbox_validation_report.md"
    report.write_text(validation_report_markdown(registry), encoding="utf-8")
    return out


def load_registry(root: Path) -> dict[str, Any]:
    path = root / "toolbox_registry.json"
    if not path.exists():
        save_registry(root)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    path = save_registry(root)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

