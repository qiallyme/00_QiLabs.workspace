from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .manifest_utils import slugify, titleize_slug, write_manifest

SCRIPT_HEADER = '''from __future__ import annotations\n\n"""\nQiLabs Toolbox Tool: {name}\n\n{description}\n"""\n\n\ndef main() -> None:\n{body}\n\n\nif __name__ == "__main__":\n    main()\n'''

CLASS_TOOL_TEMPLATE = '''from __future__ import annotations\n\n"""\nQiLabs UI-integrated Toolbox Tool: {name}\n\n{description}\n"""\n\nimport tkinter as tk\nfrom tkinter import ttk\n\nfrom core.base_tool import BaseTool\n\n\nclass {class_name}(BaseTool):\n    def __init__(self):\n        self.cancel_requested = False\n        self.reset_run_state()\n\n    def get_name(self):\n        return {name_literal}\n\n    def build_ui(self, parent_frame):\n        self.note_var = tk.StringVar(value="")\n\n        ttk.Label(parent_frame, text={name_literal}, style="CardTitle.TLabel").pack(anchor="w")\n        ttk.Label(\n            parent_frame,\n            text={description_literal},\n            style="CardBody.TLabel",\n            wraplength=380,\n            justify="left",\n        ).pack(anchor="w", pady=(4, 12))\n\n        tk.Label(parent_frame, text="Note / input", bg="#121a2b", fg="#edf3ff", font=("Segoe UI", 9, "bold")).pack(anchor="w")\n        tk.Entry(\n            parent_frame,\n            textvariable=self.note_var,\n            bg="#10192a",\n            fg="#edf3ff",\n            insertbackground="#edf3ff",\n            relief="flat",\n        ).pack(fill="x", ipady=8, pady=(4, 10))\n\n        tk.Label(\n            parent_frame,\n            text="Use Queue Scan for a dry check and Queue Execute for live action.",\n            bg="#121a2b",\n            fg="#8ea2c7",\n            wraplength=380,\n            justify="left",\n        ).pack(anchor="w")\n\n    def execute(self, target_path, is_live, log_callback, progress_callback):\n        # is_live is False for Queue Scan and True for Queue Execute.\n        dry_run = not is_live\n        note = ""\n        try:\n            note = self.note_var.get()\n        except Exception:\n            note = ""\n\n{body}\n'''


def indent_body(body: str, spaces: int = 4) -> str:
    body = body.strip('\n')
    if not body.strip():
        body = "print('Hello from this QiLabs tool.')"
    return '\n'.join(' ' * spaces + line if line.strip() else '' for line in body.splitlines())


def class_name_from_tool_name(name: str) -> str:
    slug = slugify(name)
    parts = [p for p in slug.split('_') if p]
    class_name = ''.join(p.capitalize() for p in parts) + 'Tool'
    if not re.match(r'^[A-Za-z_]', class_name):
        class_name = 'Custom' + class_name
    return class_name


def create_tool(
    toolbox_root: Path,
    name: str,
    category: str,
    description: str,
    script_body: str,
    tool_id: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Create a standalone script-style tool. Kept for compatibility."""
    category_slug = slugify(category)
    folder_slug = slugify(name)
    tool_id = tool_id or f'{category_slug}.{folder_slug}'.replace('_', '.')
    tool_dir = toolbox_root / 'tools' / category_slug / folder_slug

    if tool_dir.exists() and not overwrite:
        raise FileExistsError(f'Tool folder already exists: {tool_dir}')

    tool_dir.mkdir(parents=True, exist_ok=True)
    script_name = f'{folder_slug}.py'
    script_path = tool_dir / script_name
    readme_path = tool_dir / 'README.md'
    init_path = tool_dir / '__init__.py'
    manifest_path = tool_dir / 'manifest.yaml'

    script = SCRIPT_HEADER.format(
        name=name.strip() or titleize_slug(folder_slug),
        description=description.strip() or 'QiLabs toolbox tool.',
        body=indent_body(script_body),
    )
    if overwrite or not script_path.exists():
        script_path.write_text(script, encoding='utf-8')
    if overwrite or not readme_path.exists():
        readme_path.write_text(f'# {name}\n\n{description}\n\n## Run\n\nThis tool is discovered by `manifest.yaml` and launched by QiLabs Toolbox Manager.\n', encoding='utf-8')
    if overwrite or not init_path.exists():
        init_path.write_text('', encoding='utf-8')

    manifest: dict[str, Any] = {
        'tool_id': tool_id,
        'name': name,
        'category': category_slug,
        'version': '0.1.0',
        'enabled': True,
        'description': description or f'{name} tool.',
        'tags': [category_slug, folder_slug],
        'launch': {
            'type': 'python',
            'target': script_name,
            'working_dir': '.',
            'open_console': True,
        },
        'conflicts': [],
    }
    write_manifest(manifest_path, manifest)
    return tool_dir


def create_class_tool(
    toolbox_root: Path,
    name: str,
    category: str,
    description: str,
    execute_body: str,
    tool_id: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Create a UI-integrated BaseTool class tool for the classic shell."""
    category_slug = slugify(category)
    folder_slug = slugify(name)
    class_name = class_name_from_tool_name(name)
    tool_id = tool_id or f'{category_slug}.{folder_slug}'.replace('_', '.')
    tool_dir = toolbox_root / 'tools' / category_slug / folder_slug

    if tool_dir.exists() and not overwrite:
        raise FileExistsError(f'Tool folder already exists: {tool_dir}')

    tool_dir.mkdir(parents=True, exist_ok=True)
    script_name = f'{folder_slug}.py'
    script_path = tool_dir / script_name
    readme_path = tool_dir / 'README.md'
    init_path = tool_dir / '__init__.py'
    manifest_path = tool_dir / 'manifest.yaml'

    if not execute_body.strip():
        execute_body = "log_callback('Nothing added yet.')\nprogress_callback(100)"

    script = CLASS_TOOL_TEMPLATE.format(
        name=name.strip() or titleize_slug(folder_slug),
        description=description.strip() or 'QiLabs UI-integrated toolbox tool.',
        class_name=class_name,
        name_literal=repr(name.strip() or titleize_slug(folder_slug)),
        description_literal=repr(description.strip() or 'QiLabs UI-integrated toolbox tool.'),
        body=indent_body(execute_body, spaces=8),
    )
    if overwrite or not script_path.exists():
        script_path.write_text(script, encoding='utf-8')
    if overwrite or not readme_path.exists():
        readme_path.write_text(
            f'# {name}\n\n{description}\n\n## Type\n\nUI-integrated `BaseTool` class. It appears inside the classic QiLabs Toolbox shell and uses Queue Scan / Queue Execute.\n',
            encoding='utf-8',
        )
    if overwrite or not init_path.exists():
        init_path.write_text('', encoding='utf-8')

    manifest: dict[str, Any] = {
        'tool_id': tool_id,
        'name': name,
        'category': category_slug,
        'version': '0.1.0',
        'enabled': True,
        'description': description or f'{name} tool.',
        'tags': [category_slug, folder_slug, 'native_class'],
        'class_name': class_name,
        'launch': {
            'type': 'native_class',
            'target': script_name,
            'working_dir': '.',
            'open_console': False,
        },
        'ui': {
            'type': 'classic_base_tool',
            'class_name': class_name,
        },
        'conflicts': [],
    }
    write_manifest(manifest_path, manifest)
    return tool_dir
