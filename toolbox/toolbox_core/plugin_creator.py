from __future__ import annotations

from pathlib import Path

from .manifest_utils import slugify, write_manifest


NATIVE_TEMPLATE = '''from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class QiPlugin:
    plugin_id = "{plugin_id}"
    name = "{name}"
    category = "{category}"
    description = "{description}"

    def build_view(self, host, parent):
        frame = tk.Frame(parent, bg=host.colors["panel"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=self.name, bg=host.colors["panel"], fg=host.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame, text=self.description, bg=host.colors["panel"], fg=host.colors["muted"], wraplength=760, justify="left").pack(anchor="w", pady=(6, 16))

        ttk.Button(frame, text="Run Sample Action", command=lambda: host.run_background(self.name, lambda: host.log("Hello from {name}."))).pack(anchor="w")

    def validate(self, host):
        host.log("{name}: validation OK")
'''


LEGACY_TEMPLATE = '''from __future__ import annotations

import tkinter as tk

from core.base_tool import BaseTool


class {class_name}(BaseTool):
    def get_name(self):
        return "{name}"

    def build_ui(self, parent_frame):
        self.message_var = tk.StringVar(value="Hello from {name}.")
        tk.Label(parent_frame, text="{name} settings").pack(anchor="w")
        tk.Entry(parent_frame, textvariable=self.message_var).pack(fill="x")

    def execute(self, target_path, is_dry_run, log_callback, progress_callback):
        log_callback(f"Workspace: {{target_path}}")
        log_callback(self.message_var.get())
        progress_callback(100)
'''


SCRIPT_TEMPLATE = '''from __future__ import annotations


def main() -> None:
{body}


if __name__ == "__main__":
    main()
'''


def _class_name(name: str) -> str:
    return "".join(part.capitalize() for part in slugify(name).split("_")) + "Tool"


def create_plugin(
    toolbox_root: Path,
    name: str,
    category: str,
    description: str,
    plugin_type: str = "native",
    script_body: str = "",
) -> Path:
    category_slug = slugify(category or "custom")
    slug = slugify(name)
    plugin_dir = toolbox_root / "tools" / category_slug / slug
    if plugin_dir.exists():
        raise FileExistsError(plugin_dir)
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
    (plugin_dir / "README.md").write_text(f"# {name}\n\n{description or f'{name} plugin.'}\n", encoding="utf-8")

    plugin_id = f"{category_slug}.{slug}"
    file_name = f"{slug}.py"
    class_name = "QiPlugin"
    entry_type = "plugin_v2"

    if plugin_type == "legacy":
        class_name = _class_name(name)
        source = LEGACY_TEMPLATE.format(name=name, class_name=class_name)
        entry_type = "legacy_basetool"
    elif plugin_type == "script":
        body = script_body.strip() or '    print("Hello from QiLabs Toolbox.")'
        indented = "\n".join(("    " + line if line.strip() else "") for line in body.splitlines())
        source = SCRIPT_TEMPLATE.format(body=indented)
        class_name = ""
        entry_type = "script"
    else:
        source = NATIVE_TEMPLATE.format(plugin_id=plugin_id, name=name, category=category_slug, description=description or f"{name} plugin.")

    (plugin_dir / file_name).write_text(source, encoding="utf-8")
    manifest = {
        "plugin_id": plugin_id,
        "tool_id": plugin_id,
        "name": name,
        "category": category_slug,
        "version": "0.1.0",
        "enabled": True,
        "description": description or f"{name} plugin.",
        "entry": {
            "type": entry_type,
            "target": file_name,
            "class_name": class_name,
        },
        "requirements": [],
    }
    write_manifest(plugin_dir / "manifest.yaml", manifest)
    return plugin_dir
