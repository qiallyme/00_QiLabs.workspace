from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from .manifest_utils import read_manifest, write_manifest, slugify, titleize_slug
    from .registry_builder import save_registry
    from .tool_creator import create_class_tool, create_tool
    from .tool_validator import autofix_all, validate_all, validation_report_markdown
except Exception:  # pragma: no cover - keeps packaged shell from crashing at import time
    read_manifest = write_manifest = slugify = titleize_slug = None
    save_registry = create_class_tool = create_tool = None
    autofix_all = validate_all = validation_report_markdown = None


BASETOOL_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*BaseTool[^)]*)\)\s*:")


class MiniVar:
    def __init__(self, value: Any):
        self._value = value

    def get(self):
        return self._value

    def set(self, value: Any):
        self._value = value


class MiniText:
    def __init__(self, value: str):
        self._value = value

    def get(self, *_args, **_kwargs):
        return self._value


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_read_manifest(path: Path) -> dict[str, Any]:
    if read_manifest is None:
        return _read_json(path) if path.suffix.lower() == ".json" else {}
    try:
        return read_manifest(path)
    except Exception:
        return {}


def _find_manifest_paths(toolbox_root: Path) -> list[Path]:
    tools_root = toolbox_root / "tools"
    if not tools_root.exists():
        return []
    paths = sorted(list(tools_root.rglob("manifest.yaml")) + list(tools_root.rglob("manifest.json")))
    out: list[Path] = []
    for path in paths:
        parts = set(path.parts)
        if "_pending" in parts or "__pycache__" in parts or "_archive" in parts:
            continue
        out.append(path)
    return out


def _infer_target_file(tool_dir: Path, manifest: dict[str, Any]) -> Path | None:
    launch = manifest.get("launch") if isinstance(manifest.get("launch"), dict) else {}
    target = launch.get("target") if launch else None
    if target:
        return tool_dir / str(target)

    preferred = tool_dir / f"{tool_dir.name}.py"
    if preferred.exists():
        return preferred
    for py_file in sorted(tool_dir.glob("*.py")):
        if py_file.name != "__init__.py":
            return py_file
    return None


def _detect_basetool_class(py_file: Path, manifest: dict[str, Any]) -> str | None:
    for key in ("class_name", "tool_class"):
        value = manifest.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    native = manifest.get("native") if isinstance(manifest.get("native"), dict) else {}
    value = native.get("class_name") if native else None
    if isinstance(value, str) and value.strip():
        return value.strip()

    if not py_file or not py_file.exists() or py_file.suffix.lower() != ".py":
        return None
    text = py_file.read_text(encoding="utf-8", errors="replace")
    match = BASETOOL_RE.search(text)
    return match.group(1) if match else None


def _load_class_from_file(py_file: Path, class_name: str):
    module_key = "qilabs_tool_" + re.sub(r"[^A-Za-z0-9_]", "_", str(py_file.resolve()))
    spec = importlib.util.spec_from_file_location(module_key, py_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {py_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = module
    spec.loader.exec_module(module)
    cls = getattr(module, class_name)
    return cls


def _stamp_tool(tool: Any, manifest: dict[str, Any], manifest_path: Path, toolbox_root: Path) -> Any:
    tool.toolbox_manifest = manifest
    tool.toolbox_manifest_path = manifest_path
    tool.toolbox_root = toolbox_root
    tool.toolbox_category = manifest.get("category") or _infer_category_from_path(toolbox_root, manifest_path.parent)
    tool.toolbox_tool_id = manifest.get("tool_id") or ""
    tool.toolbox_display_name = manifest.get("name") or getattr(tool, "get_name", lambda: manifest_path.parent.name)()
    if not hasattr(tool, "cancel_requested"):
        tool.cancel_requested = False
    if hasattr(tool, "reset_run_state"):
        tool.reset_run_state()
    return tool


def _infer_category_from_path(toolbox_root: Path, tool_dir: Path) -> str:
    try:
        rel = tool_dir.relative_to(toolbox_root / "tools")
        return rel.parts[0] if len(rel.parts) >= 2 else "misc"
    except Exception:
        return "misc"


class ScriptManifestTool:
    """Fallback adapter for standalone script-style tools that do not implement BaseTool."""

    toolbox_category = "misc"

    def __init__(self, toolbox_root: Path, manifest: dict[str, Any], manifest_path: Path):
        self.toolbox_root = toolbox_root
        self.manifest = manifest
        self.manifest_path = manifest_path
        self.toolbox_category = manifest.get("category") or _infer_category_from_path(toolbox_root, manifest_path.parent)
        self.toolbox_tool_id = manifest.get("tool_id") or ""
        self.toolbox_display_name = manifest.get("name") or manifest_path.parent.name
        self.cancel_requested = False
        self.reset_run_state()

    def clone_for_run(self, snapshot: dict[str, tuple[str, Any]]):
        clone = ScriptManifestTool(self.toolbox_root, dict(self.manifest), self.manifest_path)
        for name, payload in snapshot.items():
            state_type, value = payload
            if state_type == "variable":
                setattr(clone, name, MiniVar(value))
            elif state_type == "text":
                setattr(clone, name, MiniText(value))
        return clone

    def reset_run_state(self):
        self._run_status = "success"
        self._run_message = ""

    def set_run_status(self, status: str, message: str = ""):
        self._run_status = status
        self._run_message = message

    def get_run_status(self):
        return self._run_status, self._run_message

    def get_name(self):
        return self.toolbox_display_name

    def _tool_dir(self) -> Path:
        return self.manifest_path.parent

    def _target_path(self) -> Path | None:
        return _infer_target_file(self._tool_dir(), self.manifest)

    def build_ui(self, parent_frame):
        self.open_console_var = tk.BooleanVar(value=bool((self.manifest.get("launch") or {}).get("open_console", True)))
        self.extra_args_var = tk.StringVar(value="")

        tk.Label(parent_frame, text=self.get_name(), bg="#121a2b", fg="#edf3ff", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(parent_frame, text=self.manifest.get("description", "Standalone script tool."), bg="#121a2b", fg="#8ea2c7", wraplength=390, justify="left").pack(anchor="w", pady=(6, 12))

        details = tk.Frame(parent_frame, bg="#182338", padx=12, pady=10)
        details.pack(fill="x", pady=(0, 12))
        rows = [
            ("Tool ID", self.toolbox_tool_id),
            ("Category", self.toolbox_category),
            ("Manifest", str(self.manifest_path)),
            ("Target", str(self._target_path() or "missing")),
            ("Mode", "Standalone script fallback"),
        ]
        for label, value in rows:
            tk.Label(details, text=label, bg="#182338", fg="#7ee7de", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(details, text=value, bg="#182338", fg="#8ea2c7", wraplength=380, justify="left").pack(anchor="w", pady=(0, 6))

        tk.Label(parent_frame, text="Extra command args", bg="#121a2b", fg="#edf3ff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Entry(parent_frame, textvariable=self.extra_args_var, bg="#10192a", fg="#edf3ff", insertbackground="#edf3ff", relief="flat").pack(fill="x", ipady=8, pady=(4, 10))
        tk.Checkbutton(parent_frame, text="Open in separate console", variable=self.open_console_var, bg="#121a2b", fg="#edf3ff", selectcolor="#202d45", activebackground="#121a2b", activeforeground="#edf3ff").pack(anchor="w")

    def _command(self) -> list[str]:
        launch = self.manifest.get("launch") if isinstance(self.manifest.get("launch"), dict) else {}
        launch_type = (launch.get("type") or "python").lower()
        target = self._target_path()
        if target is None:
            raise FileNotFoundError("No launch target found.")
        if launch_type in {"python", "native_class"} or target.suffix.lower() == ".py":
            cmd = [sys.executable, str(target)] if getattr(sys, "frozen", False) else ["py", str(target)]
        elif launch_type == "bat" or target.suffix.lower() == ".bat":
            cmd = ["cmd", "/c", str(target)]
        elif launch_type == "powershell" or target.suffix.lower() == ".ps1":
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(target)]
        else:
            cmd = [str(target)]
        try:
            args = self.extra_args_var.get().strip()
            if args:
                cmd += args.split()
        except Exception:
            pass
        return cmd

    def execute(self, target_path, is_live, log_callback, progress_callback):
        target = self._target_path()
        log_callback(f"Tool: {self.get_name()}")
        log_callback(f"Manifest: {self.manifest_path}")
        log_callback(f"Target: {target}")
        log_callback(f"Workspace: {target_path}")
        progress_callback(10)

        if target is None or not target.exists():
            self.set_run_status("failed", "Launch target missing.")
            log_callback("ERROR: launch target missing.")
            return

        if not is_live:
            progress_callback(100)
            log_callback("SCAN OK: script target exists. No code executed.")
            return

        cmd = self._command()
        log_callback("EXECUTE: " + " ".join(cmd))
        progress_callback(25)

        open_console = True
        try:
            open_console = bool(self.open_console_var.get())
        except Exception:
            open_console = True

        if open_console:
            creationflags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0
            subprocess.Popen(["cmd", "/k"] + cmd, cwd=str(self._tool_dir()), creationflags=creationflags)
            progress_callback(100)
            log_callback("Launched in separate console.")
            return

        proc = subprocess.Popen(cmd, cwd=str(self._tool_dir()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout or []:
            if getattr(self, "cancel_requested", False):
                proc.terminate()
                self.set_run_status("warning", "Cancelled")
                log_callback("Cancelled.")
                return
            log_callback(line.rstrip())
        code = proc.wait()
        progress_callback(100)
        if code:
            self.set_run_status("failed", f"Exit code {code}")
            log_callback(f"ERROR: exit code {code}")
        else:
            log_callback("Completed.")


class BrokenTool:
    toolbox_category = "broken"

    def __init__(self, name: str, path: str, error: str):
        self._name = name
        self.path = path
        self.error = error
        self.cancel_requested = False
        self.reset_run_state()

    def reset_run_state(self):
        self._run_status = "failed"
        self._run_message = self.error

    def get_run_status(self):
        return self._run_status, self._run_message

    def get_name(self):
        return f"BROKEN: {self._name}"

    def build_ui(self, parent_frame):
        tk.Label(parent_frame, text=self.get_name(), bg="#121a2b", fg="#ff6b6b", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(parent_frame, text=self.path, bg="#121a2b", fg="#8ea2c7", wraplength=390, justify="left").pack(anchor="w", pady=(6, 12))
        text = tk.Text(parent_frame, height=16, bg="#08111e", fg="#d4f7db", insertbackground="#d4f7db", relief="flat", wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.error)
        text.configure(state="disabled")

    def execute(self, target_path, is_live, log_callback, progress_callback):
        log_callback("This tool could not be loaded.")
        log_callback(self.error)
        progress_callback(100)


class ToolboxManagerTool:
    toolbox_category = "system"
    toolbox_display_name = "Toolbox Manager"
    toolbox_tool_id = "system.toolbox_manager"

    def __init__(self, toolbox_root: Path):
        self.toolbox_root = toolbox_root
        self.cancel_requested = False
        self.reset_run_state()

    def clone_for_run(self, snapshot: dict[str, tuple[str, Any]]):
        clone = ToolboxManagerTool(self.toolbox_root)
        for name, payload in snapshot.items():
            state_type, value = payload
            if state_type == "variable":
                setattr(clone, name, MiniVar(value))
            elif state_type == "text":
                setattr(clone, name, MiniText(value))
        return clone

    def reset_run_state(self):
        self._run_status = "success"
        self._run_message = ""

    def set_run_status(self, status, message=""):
        self._run_status = status
        self._run_message = message

    def get_run_status(self):
        return self._run_status, self._run_message

    def get_name(self):
        return "Toolbox Manager"

    def build_ui(self, parent_frame):
        self.new_name_var = tk.StringVar(value="")
        self.new_category_var = tk.StringVar(value="custom")
        self.status_var = tk.StringVar(value="Ready.")

        tk.Label(parent_frame, text="Toolbox Manager", bg="#121a2b", fg="#edf3ff", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(parent_frame, text="Validate, auto-fix, and create dynamic tools without rebuilding the EXE.", bg="#121a2b", fg="#8ea2c7", wraplength=390, justify="left").pack(anchor="w", pady=(6, 12))

        row = tk.Frame(parent_frame, bg="#121a2b")
        row.pack(fill="x", pady=(0, 12))
        self._button(row, "Refresh Registry", self._refresh_registry).pack(side="left", padx=(0, 6))
        self._button(row, "Validate", self._validate).pack(side="left", padx=6)
        self._button(row, "Auto-Fix", self._autofix).pack(side="left", padx=6)

        create = tk.Frame(parent_frame, bg="#182338", padx=12, pady=12)
        create.pack(fill="both", expand=True, pady=(0, 12))
        tk.Label(create, text="Create New UI-Integrated Python Tool", bg="#182338", fg="#edf3ff", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(create, text="Paste the body that should run inside execute(). The manager wraps it in the BaseTool class, manifest, README, and __init__.py.", bg="#182338", fg="#8ea2c7", wraplength=380, justify="left").pack(anchor="w", pady=(3, 10))

        tk.Label(create, text="Tool name", bg="#182338", fg="#7ee7de", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(create, textvariable=self.new_name_var, bg="#10192a", fg="#edf3ff", insertbackground="#edf3ff", relief="flat").pack(fill="x", ipady=7, pady=(3, 8))
        tk.Label(create, text="Category", bg="#182338", fg="#7ee7de", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(create, textvariable=self.new_category_var, bg="#10192a", fg="#edf3ff", insertbackground="#edf3ff", relief="flat").pack(fill="x", ipady=7, pady=(3, 8))
        tk.Label(create, text="Description", bg="#182338", fg="#7ee7de", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.description_text = tk.Text(create, height=3, bg="#10192a", fg="#edf3ff", insertbackground="#edf3ff", relief="flat", wrap="word")
        self.description_text.pack(fill="x", pady=(3, 8))
        tk.Label(create, text="Execute body", bg="#182338", fg="#7ee7de", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.body_text = tk.Text(create, height=9, bg="#08111e", fg="#d4f7db", insertbackground="#d4f7db", relief="flat", wrap="none")
        self.body_text.pack(fill="both", expand=True, pady=(3, 8))
        self.body_text.insert("1.0", "log_callback('Hello from my new tool')\nprogress_callback(100)")

        self._button(create, "Create + Validate Tool", self._create_tool).pack(anchor="w", pady=(4, 0))
        tk.Label(parent_frame, textvariable=self.status_var, bg="#121a2b", fg="#7ee7de", wraplength=390, justify="left").pack(anchor="w")

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#4ecdc4", fg="#08111e", activebackground="#4ecdc4", activeforeground="#08111e", relief="flat", bd=0, padx=12, pady=8, cursor="hand2")

    def _refresh_registry(self):
        if save_registry is None:
            self.status_var.set("Registry builder unavailable.")
            return
        path = save_registry(self.toolbox_root)
        self.status_var.set(f"Registry refreshed: {path}")
        messagebox.showinfo("Registry Refreshed", "Registry refreshed. Restart the toolbox or relaunch to reload the left rail.")

    def _validate(self):
        if validate_all is None:
            self.status_var.set("Validator unavailable.")
            return
        result = validate_all(self.toolbox_root)
        report = validation_report_markdown(result) if validation_report_markdown else json.dumps(result, indent=2)
        out = self.toolbox_root / "toolbox_validation_report.md"
        out.write_text(report, encoding="utf-8")
        self.status_var.set(f"Validation complete: errors={result.get('errors')} warnings={result.get('warnings')}")
        os.startfile(out) if os.name == "nt" else None

    def _autofix(self):
        if autofix_all is None:
            self.status_var.set("Autofix unavailable.")
            return
        if not messagebox.askyesno("Auto-Fix Safe Issues", "Apply safe manifest fixes now?"):
            return
        result = autofix_all(self.toolbox_root, dry_run=False)
        if save_registry:
            save_registry(self.toolbox_root)
        self.status_var.set(f"Auto-fix complete: {len(result.get('findings', []))} findings processed.")
        messagebox.showinfo("Auto-Fix Complete", "Safe fixes applied. Restart the toolbox or relaunch to reload tools.")

    def _create_tool(self):
        if create_class_tool is None:
            self.status_var.set("Class tool creator unavailable.")
            return
        name = self.new_name_var.get().strip()
        category = self.new_category_var.get().strip() or "custom"
        description = self.description_text.get("1.0", "end").strip()
        body = self.body_text.get("1.0", "end").strip()
        if not name:
            messagebox.showerror("Missing Name", "Give the tool a name first.")
            return
        try:
            tool_dir = create_class_tool(self.toolbox_root, name, category, description, body)
            if save_registry:
                save_registry(self.toolbox_root)
            self.status_var.set(f"Created: {tool_dir}")
            messagebox.showinfo("Tool Created", f"Created tool:\n{tool_dir}\n\nRestart the toolbox or relaunch to see it in the left rail.")
        except Exception as exc:
            self.status_var.set(f"Create failed: {exc}")
            messagebox.showerror("Create Failed", str(exc))

    def execute(self, target_path, is_live, log_callback, progress_callback):
        log_callback("Toolbox Manager")
        if not is_live:
            if validate_all is None:
                self.set_run_status("failed", "Validator unavailable.")
                log_callback("Validator unavailable.")
                return
            result = validate_all(self.toolbox_root)
            out = self.toolbox_root / "toolbox_validation_report.md"
            out.write_text(validation_report_markdown(result), encoding="utf-8")
            log_callback(f"Validation: errors={result.get('errors')} warnings={result.get('warnings')}")
            log_callback(str(out))
            progress_callback(100)
            return
        if autofix_all:
            result = autofix_all(self.toolbox_root, dry_run=False)
            log_callback(f"Auto-fix findings processed: {len(result.get('findings', []))}")
        if save_registry:
            path = save_registry(self.toolbox_root)
            log_callback(f"Registry refreshed: {path}")
        progress_callback(100)


def load_classic_tools(toolbox_root: Path) -> list[Any]:
    """Load UI-integrated BaseTool class tools from manifests at runtime.

    This is the compatibility layer that preserves the old QiOneShell run queue/UI contract.
    """
    if str(toolbox_root) not in sys.path:
        sys.path.insert(0, str(toolbox_root))

    tools: list[Any] = [ToolboxManagerTool(toolbox_root)]
    seen_ids = {"system.toolbox_manager"}

    for manifest_path in _find_manifest_paths(toolbox_root):
        manifest = _safe_read_manifest(manifest_path)
        if not manifest.get("enabled", True):
            continue
        tool_id = manifest.get("tool_id") or str(manifest_path)
        if tool_id in seen_ids:
            continue
        seen_ids.add(tool_id)

        tool_dir = manifest_path.parent
        py_file = _infer_target_file(tool_dir, manifest)
        class_name = _detect_basetool_class(py_file, manifest) if py_file else None

        try:
            if class_name and py_file:
                cls = _load_class_from_file(py_file, class_name)
                instance = cls()
                tools.append(_stamp_tool(instance, manifest, manifest_path, toolbox_root))
            else:
                tools.append(ScriptManifestTool(toolbox_root, manifest, manifest_path))
        except Exception:
            name = manifest.get("name") or manifest_path.parent.name
            error = traceback.format_exc()
            tools.append(BrokenTool(name, str(manifest_path), error))

    return tools
