from __future__ import annotations

from pathlib import Path
from typing import Any

from .plugin_registry import build_registry, save_registry


def build_tool_registry(toolbox_root: Path) -> dict[str, Any]:
    return build_registry(toolbox_root)
