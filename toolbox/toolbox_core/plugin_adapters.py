from __future__ import annotations

import importlib.util
import inspect
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import messagebox, ttk


class ScrollFrame(tk.Frame):
    """Small reusable scroll frame for legacy tools with tall forms."""

    def __init__(self, parent: tk.Widget, *, bg: str):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_wheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")


def _toolbox_root_for(path: Path) -> Path:
    parts = path.resolve().parts
    if "tools" in parts:
        return Path(*parts[: parts.index("tools")])
    return path.resolve().parent


def _module_name_for(path: Path) -> str:
    parts = path.resolve().with_suffix("").parts
    if "tools" in parts:
        index = parts.index("tools")
        raw = ".".join(parts[index:])
    else:
        raw = "qilabs_plugin_" + str(abs(hash(str(path.resolve()))))
    return re.sub(r"[^A-Za-z0-9_.]", "_", raw)


def load_module_from_file(path: Path):
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    root = _toolbox_root_for(path)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    module_name = _module_name_for(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _looks_like_native_plugin(cls: type) -> bool:
    return callable(getattr(cls, "build_view", None))


def _looks_like_legacy_tool(cls: type) -> bool:
    return callable(getattr(cls, "build_ui", None)) and callable(getattr(cls, "execute", None))


def find_class_in_module(module: Any, preferred: str = "", mode: str = "") -> type:
    if preferred and hasattr(module, preferred):
        obj = getattr(module, preferred)
        if inspect.isclass(obj):
            return obj

    classes = [obj for _name, obj in inspect.getmembers(module, inspect.isclass) if getattr(obj, "__module__", None) == module.__name__]

    if mode == "plugin_v2":
        for cls in classes:
            if _looks_like_native_plugin(cls):
                return cls
    if mode == "legacy_basetool":
        for cls in classes:
            if _looks_like_legacy_tool(cls):
                return cls

    for cls in classes:
        if _looks_like_native_plugin(cls):
            return cls
    for cls in classes:
        if _looks_like_legacy_tool(cls):
            return cls

    raise AttributeError(f"No usable plugin class found in {getattr(module, '__file__', module)}")


def load_class_from_file(path: Path, class_name: str = "", mode: str = "") -> type:
    module = load_module_from_file(path)
    return find_class_in_module(module, class_name, mode)


class PluginAdapter:
    def __init__(self, root: Path, record: dict[str, Any]):
        self.root = root
        self.record = record
        self.plugin_id = record.get("plugin_id", "")
        self.name = record.get("name", self.plugin_id)
        self.category = record.get("category", "uncategorized")
        self.description = record.get("description", "")
        self.plugin_dir = root / record.get("path", "")
        self.manifest_path = root / record.get("manifest_path", "")
        self.entry = record.get("entry", {})

    @property
    def target_path(self) -> Path:
        return self.plugin_dir / str(self.entry.get("target") or "")

    def activate(self, host: Any) -> None:
        pass

    def deactivate(self, host: Any) -> None:
        pass

    def validate(self, host: Any) -> None:
        host.validate_plugin(self.plugin_id)

    def build_view(self, host: Any, parent: tk.Widget) -> None:
        raise NotImplementedError


class NativePluginAdapter(PluginAdapter):
    def __init__(self, root: Path, record: dict[str, Any]):
        super().__init__(root, record)
        cls = load_class_from_file(self.target_path, self.entry.get("class_name") or "", "plugin_v2")
        self.instance = cls()
        for attr in ("plugin_id", "name", "category", "description"):
            if hasattr(self.instance, attr):
                setattr(self, attr, getattr(self.instance, attr))

    def activate(self, host: Any) -> None:
        if hasattr(self.instance, "activate"):
            self.instance.activate(host)

    def deactivate(self, host: Any) -> None:
        if hasattr(self.instance, "deactivate"):
            self.instance.deactivate(host)

    def validate(self, host: Any) -> None:
        if hasattr(self.instance, "validate"):
            result = self.instance.validate(host)
            if result:
                host.log(str(result))
            return
        super().validate(host)

    def build_view(self, host: Any, parent: tk.Widget) -> None:
        self.instance.build_view(host, parent)


class LegacyBaseToolAdapter(PluginAdapter):
    def __init__(self, root: Path, record: dict[str, Any]):
        super().__init__(root, record)
        cls = load_class_from_file(self.target_path, self.entry.get("class_name") or "", "legacy_basetool")
        self.tool = cls()
        if hasattr(self.tool, "toolbox_manifest"):
            self.tool.toolbox_manifest = record

    def build_view(self, host: Any, parent: tk.Widget) -> None:
        shell = tk.Frame(parent, bg=host.colors["panel"])
        shell.pack(fill="both", expand=True)

        action_bar = tk.Frame(shell, bg=host.colors["panel"])
        action_bar.pack(fill="x", pady=(0, 8))
        tk.Button(action_bar, text="Scan", command=lambda: self._run(host, False), bg=host.colors["success"], fg="#061014", relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left")
        tk.Button(action_bar, text="Execute", command=lambda: self._confirm_live(host), bg=host.colors["danger"], fg="white", relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(action_bar, text="Cancel", command=self._cancel, bg=host.colors["warning"], fg="#16120a", relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(action_bar, text="Open Folder", command=lambda: host.open_folder(str(self.plugin_dir)), bg=host.colors["panel_3"], fg=host.colors["text"], relief="flat", padx=12, pady=7, cursor="hand2").pack(side="right")

        scroll = ScrollFrame(shell, bg=host.colors["panel"])
        scroll.pack(fill="both", expand=True)
        self.tool.build_ui(scroll.inner)

    def _cancel(self) -> None:
        setattr(self.tool, "cancel_requested", True)

    def _confirm_live(self, host: Any) -> None:
        if messagebox.askyesno("Execute Tool", f"Run {self.name} in apply/live mode?"):
            self._run(host, True)

    def _run(self, host: Any, is_live: bool) -> None:
        setattr(self.tool, "cancel_requested", False)
        if hasattr(self.tool, "reset_run_state"):
            self.tool.reset_run_state()

        def work() -> None:
            self.tool.execute(
                host.get_workspace(),
                is_live,
                host.log,
                lambda value: host.set_status(f"{self.name}: {value}%"),
            )

        mode = "Execute" if is_live else "Scan"
        host.run_background(f"{self.name} - {mode}", work, on_done=lambda _result: host.set_status(f"{self.name} complete"))


class ScriptPluginAdapter(PluginAdapter):
    def build_view(self, host: Any, parent: tk.Widget) -> None:
        wrap = tk.Frame(parent, bg=host.colors["panel"])
        wrap.pack(fill="both", expand=True)

        tk.Label(wrap, text=self.name, bg=host.colors["panel"], fg=host.colors["text"], font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(wrap, text=self.description or "Script plugin.", bg=host.colors["panel"], fg=host.colors["muted"], wraplength=860, justify="left").pack(anchor="w", pady=(4, 10))

        details = tk.Frame(wrap, bg=host.colors["panel_2"], padx=10, pady=8)
        details.pack(fill="x", pady=(0, 10))
        for label, value in (
            ("Plugin ID", self.plugin_id),
            ("Entry", f"{self.entry.get('type')} / {self.entry.get('target')}"),
            ("Folder", str(self.plugin_dir)),
        ):
            row = tk.Frame(details, bg=host.colors["panel_2"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", width=10, anchor="w", bg=host.colors["panel_2"], fg=host.colors["accent"], font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, text=value, anchor="w", bg=host.colors["panel_2"], fg=host.colors["text"], wraplength=760, justify="left").pack(side="left", fill="x", expand=True)

        controls = tk.Frame(wrap, bg=host.colors["panel"])
        controls.pack(fill="x", pady=(0, 10))
        tk.Button(controls, text="Run", command=lambda: self._run(host), bg=host.colors["accent"], fg="#061014", relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left")
        tk.Button(controls, text="Open Folder", command=lambda: host.open_folder(str(self.plugin_dir)), bg=host.colors["panel_3"], fg=host.colors["text"], relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(controls, text="Manifest", command=lambda: host.open_file(str(self.manifest_path)), bg=host.colors["panel_3"], fg=host.colors["text"], relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(controls, text="Validate", command=lambda: host.validate_plugin(self.plugin_id), bg=host.colors["panel_3"], fg=host.colors["text"], relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))

        if self.record.get("requirements"):
            tk.Button(controls, text="Install Requirements", command=lambda: host.install_requirements(self.record.get("requirements", [])), bg=host.colors["warning"], fg="#16120a", relief="flat", padx=12, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))

    def _command(self, action: dict[str, Any] | None = None) -> list[str]:
        target = self.target_path
        entry_type = str(self.entry.get("type") or "").lower()
        if action and action.get("command"):
            return [str(action["command"])]
        if entry_type == "bat" or target.suffix.lower() == ".bat":
            return ["cmd", "/c", str(target)]
        if entry_type == "exe" or target.suffix.lower() == ".exe":
            return [str(target)]
        if target.suffix.lower() == ".ps1":
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target)]
        python = sys.executable if not getattr(sys, "frozen", False) else "py"
        return [python, str(target)]

    def _run(self, host: Any, action: dict[str, Any] | None = None) -> None:
        def work() -> None:
            if not self.target_path.exists():
                raise FileNotFoundError(self.target_path)
            cmd = self._command(action)
            host.log("RUN: " + " ".join(cmd))
            proc = subprocess.Popen(cmd, cwd=str(self.plugin_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout or []:
                host.log(line.rstrip())
            code = proc.wait()
            if code:
                raise RuntimeError(f"Exit code {code}")

        label = action.get("label") if action else "Run"
        host.run_background(f"{self.name} - {label}", work, on_done=lambda _result: host.set_status(f"{self.name} finished"))


class BrokenPluginAdapter(PluginAdapter):
    def __init__(self, root: Path, record: dict[str, Any], error: BaseException | str):
        super().__init__(root, record)
        if isinstance(error, str):
            self.error_text = error
        else:
            self.error_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    def build_view(self, host: Any, parent: tk.Widget) -> None:
        tk.Label(parent, text=f"Could not load {self.name}", bg=host.colors["panel"], fg=host.colors["danger"], font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(parent, text=str(self.manifest_path), bg=host.colors["panel"], fg=host.colors["muted"], wraplength=880, justify="left").pack(anchor="w", pady=(4, 10))
        if self.record.get("requirements"):
            tk.Button(parent, text="Install Requirements", command=lambda: host.install_requirements(self.record.get("requirements", [])), bg=host.colors["warning"], fg="#16120a", relief="flat", padx=12, pady=7, cursor="hand2").pack(anchor="w", pady=(0, 10))
        text = tk.Text(parent, bg=host.colors["console_bg"], fg=host.colors["console_text"], insertbackground=host.colors["console_text"], relief="flat", wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.error_text)
        text.configure(state="disabled")


def adapter_for(root: Path, record: dict[str, Any]) -> PluginAdapter:
    entry_type = str((record.get("entry") or {}).get("type") or "script").lower()
    try:
        if entry_type == "plugin_v2":
            return NativePluginAdapter(root, record)
        if entry_type == "legacy_basetool":
            return LegacyBaseToolAdapter(root, record)
        return ScriptPluginAdapter(root, record)
    except Exception as exc:
        return BrokenPluginAdapter(root, record, exc)
