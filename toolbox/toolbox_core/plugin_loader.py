from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .plugin_adapters import PluginAdapter, adapter_for
from .plugin_registry import load_registry as _load_registry
from .plugin_registry import save_registry


def toolbox_root_from_here(current_file: str | None = None) -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    if current_file:
        return Path(current_file).resolve().parent
    return Path.cwd()


def load_registry(toolbox_root: Path) -> dict[str, Any]:
    return _load_registry(toolbox_root)


def load_plugins(toolbox_root: Path, refresh: bool = False) -> list[PluginAdapter]:
    if refresh:
        save_registry(toolbox_root)
    registry = load_registry(toolbox_root)
    plugins = registry.get("plugins") or registry.get("tools") or []
    adapters: list[PluginAdapter] = []
    for record in plugins:
        if record.get("enabled", True):
            adapters.append(adapter_for(toolbox_root, record))
    return adapters


def run_tool(toolbox_root: Path, tool: dict[str, Any]) -> None:
    """Backwards-compatible helper for the older manager UI."""
    plugin_dir = toolbox_root / tool.get("path", "")
    entry = tool.get("entry") or tool.get("launch") or {}
    target = entry.get("target")
    if not target:
        raise RuntimeError("Tool has no entry.target")
    target_path = plugin_dir / target
    if not target_path.exists():
        raise FileNotFoundError(target_path)

    entry_type = (entry.get("type") or "").lower()
    if entry_type in {"bat", "batch"} or target_path.suffix.lower() == ".bat":
        cmd = ["cmd", "/k", str(target_path)]
    elif entry_type == "exe" or target_path.suffix.lower() == ".exe":
        cmd = [str(target_path)]
    elif target_path.suffix.lower() == ".ps1":
        cmd = ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", str(target_path)]
    else:
        cmd = ["cmd", "/k", "py", str(target_path)]

    flags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0
    subprocess.Popen(cmd, cwd=str(plugin_dir), creationflags=flags)
