from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Callable

from .plugin_registry import build_registry, save_registry, validation_report_markdown


class PluginHost:
    def __init__(
        self,
        toolbox_root: Path,
        workspace_getter: Callable[[], str],
        workspace_setter: Callable[[str], None],
        log_callback: Callable[[str], None],
        status_callback: Callable[[str], None],
        refresh_callback: Callable[[], None],
        ui_dispatch: Callable[[Callable[[], None]], None],
        colors: dict[str, str],
    ):
        self.toolbox_root = toolbox_root
        self._workspace_getter = workspace_getter
        self._workspace_setter = workspace_setter
        self._log_callback = log_callback
        self._status_callback = status_callback
        self._refresh_callback = refresh_callback
        self._ui_dispatch = ui_dispatch
        self.colors = colors
        self.jobs: "queue.Queue[str]" = queue.Queue()

    def log(self, message: str) -> None:
        self._ui_dispatch(lambda: self._log_callback(str(message)))

    def error(self, message: str) -> None:
        self._ui_dispatch(lambda: self._log_callback(f"ERROR: {message}"))
        self.set_status(f"Error: {message}")

    def set_status(self, message: str) -> None:
        self._ui_dispatch(lambda: self._status_callback(str(message)))

    def get_workspace(self) -> str:
        return self._workspace_getter()

    def set_workspace(self, path: str) -> None:
        self._ui_dispatch(lambda: self._workspace_setter(path))

    def open_url(self, url: str) -> None:
        webbrowser.open(url)

    def open_file(self, path: str) -> None:
        target = Path(path)
        if not target.is_absolute():
            target = self.toolbox_root / target
        os.startfile(target) if os.name == "nt" else webbrowser.open(target.as_uri())

    def open_folder(self, path: str) -> None:
        target = Path(path)
        if not target.is_absolute():
            target = self.toolbox_root / target
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(target) if os.name == "nt" else webbrowser.open(target.as_uri())

    def run_background(self, name: str, callable_obj: Callable[[], Any], on_done: Callable[[Any], None] | None = None) -> threading.Thread:
        def worker() -> None:
            self.log(f"START: {name}")
            self.set_status(f"Running: {name}")
            try:
                result = callable_obj()
            except Exception:
                result = None
                self.error(traceback.format_exc())
            else:
                self.log(f"DONE: {name}")
            finally:
                if on_done:
                    self._ui_dispatch(lambda: on_done(result))

        thread = threading.Thread(target=worker, name=f"QiLabs-{name}", daemon=True)
        thread.start()
        return thread

    def install_requirements(self, requirements: list[str]) -> None:
        if not requirements:
            self.log("No requirements listed.")
            return

        def work() -> None:
            cmd = [sys.executable, "-m", "pip", "install", *requirements]
            self.log("INSTALL: " + " ".join(cmd))
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout or []:
                self.log(line.rstrip())
            code = proc.wait()
            if code:
                raise RuntimeError(f"pip exited with {code}")

        self.run_background("Install requirements", work, on_done=lambda _result: self.refresh_plugins())

    def refresh_plugins(self) -> None:
        save_registry(self.toolbox_root)
        self._ui_dispatch(self._refresh_callback)

    def validate_plugin(self, plugin_id: str | None = None) -> dict[str, Any]:
        registry = build_registry(self.toolbox_root)
        if plugin_id:
            findings = [f for f in registry.get("findings", []) if f.get("plugin_id") == plugin_id]
            filtered = dict(registry)
            filtered["findings"] = findings
            filtered["errors"] = sum(1 for f in findings if f.get("severity") == "ERROR")
            filtered["warnings"] = sum(1 for f in findings if f.get("severity") == "WARNING")
            report = validation_report_markdown(filtered)
        else:
            report = validation_report_markdown(registry)
        out = self.toolbox_root / "toolbox_validation_report.md"
        out.write_text(report, encoding="utf-8")
        self.log(report.rstrip())
        self.set_status(f"Validation: {registry.get('errors', 0)} errors, {registry.get('warnings', 0)} warnings")
        return registry
