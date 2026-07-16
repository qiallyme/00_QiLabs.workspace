from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from core.base_tool import BaseTool
except Exception:
    class BaseTool:  # fallback for native plugin mode if core is unavailable
        pass


PLUGIN_DIR = Path(__file__).resolve().parent
TOOLBOX_ROOT = PLUGIN_DIR.parents[2]
HOUSEKEEPING_DIR = TOOLBOX_ROOT / "tools/checkers/housekeeping"
HOUSEKEEPING_UI = HOUSEKEEPING_DIR / "housekeeping_ui.py"
LAUNCH_BAT = HOUSEKEEPING_DIR / "launch_housekeeping.bat"


def _open_path(path: Path) -> None:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if os.name == "nt":
        os.startfile(str(path))
    else:
        import webbrowser
        webbrowser.open(path.as_uri())


def _launch_housekeeping() -> None:
    if not HOUSEKEEPING_DIR.exists():
        raise FileNotFoundError(f"Housekeeping folder not found: {HOUSEKEEPING_DIR}")
    if LAUNCH_BAT.exists() and os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", "", str(LAUNCH_BAT)], cwd=str(HOUSEKEEPING_DIR))
        return
    if HOUSEKEEPING_UI.exists():
        subprocess.Popen([sys.executable, str(HOUSEKEEPING_UI)], cwd=str(HOUSEKEEPING_DIR))
        return
    raise FileNotFoundError(f"Housekeeping UI not found: {HOUSEKEEPING_UI}")


def _latest_file(folder: Path, pattern: str) -> Path | None:
    if not folder.exists():
        return None
    found = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0] if found else None


class QiPlugin:
    plugin_id = "system.housekeeping.console"
    name = "Housekeeping Console"
    category = "system"
    description = "Review/apply/undo QiLabs housekeeping plans from the toolbox."

    def build_view(self, host, parent):
        colors = getattr(host, "colors", {})
        panel = colors.get("panel", "#151d26")
        panel_2 = colors.get("panel_2", "#1c2732")
        text = colors.get("text", "#edf2f7")
        muted = colors.get("muted", "#9fb0bf")
        accent = colors.get("accent", "#62d6c4")
        danger = colors.get("danger", "#ff6b6b")

        root = tk.Frame(parent, bg=panel)
        root.pack(fill="both", expand=True)

        tk.Label(root, text="ðŸ§¹ Housekeeping Console", bg=panel, fg=text, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(
            root,
            text="Launch the full housekeeping workflow, then open summaries, reports, manifests, logs, and saved plans without digging through folders.",
            bg=panel,
            fg=muted,
            wraplength=860,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 12))

        status = tk.StringVar(value=self._status_text())
        status_box = tk.Frame(root, bg=panel_2, padx=12, pady=10)
        status_box.pack(fill="x", pady=(0, 12))
        tk.Label(status_box, textvariable=status, bg=panel_2, fg=text, justify="left", anchor="w", font=("Segoe UI", 10)).pack(anchor="w", fill="x")

        def safe(action_name, fn):
            try:
                fn()
                status.set(self._status_text())
                host.log(f"Housekeeping: {action_name}")
                host.set_status(f"Housekeeping: {action_name}")
            except Exception as exc:
                message = f"{action_name} failed: {exc}"
                status.set(message)
                host.error(message)
                messagebox.showerror("Housekeeping Console", message)

        actions = tk.Frame(root, bg=panel)
        actions.pack(fill="x", pady=(0, 10))

        self._button(actions, "Open Housekeeping Console", lambda: safe("opened console", _launch_housekeeping), accent, "#08111e").pack(side="left", padx=(0, 8), pady=(0, 8))
        self._button(actions, "Open Summary", lambda: safe("opened latest summary", lambda: _open_path(_latest_file(HOUSEKEEPING_DIR / "summaries", "housekeeping-summary-*.md") or HOUSEKEEPING_DIR / "summaries")), panel_2, text).pack(side="left", padx=(0, 8), pady=(0, 8))
        self._button(actions, "Open Report", lambda: safe("opened latest report", lambda: _open_path(_latest_file(HOUSEKEEPING_DIR / "reports", "housekeeping-report-*.md") or HOUSEKEEPING_DIR / "reports")), panel_2, text).pack(side="left", padx=(0, 8), pady=(0, 8))
        self._button(actions, "Refresh Status", lambda: status.set(self._status_text()), panel_2, text).pack(side="left", padx=(0, 8), pady=(0, 8))

        folders = tk.LabelFrame(root, text="Housekeeping folders", bg=panel, fg=accent, padx=10, pady=10, bd=1, relief="flat")
        folders.pack(fill="x", pady=(4, 12))

        for label, rel in [
            ("Plans", "plans"),
            ("Manifests", "manifests"),
            ("Summaries", "summaries"),
            ("Reports", "reports"),
            ("Logs", "logs"),
            ("Backups", "backups"),
        ]:
            self._button(folders, label, lambda r=rel: safe(f"opened {r}", lambda: _open_path(HOUSEKEEPING_DIR / r)), panel_2, text).pack(side="left", padx=(0, 8), pady=4)

        note = tk.Text(root, height=8, bg=colors.get("console_bg", "#071018"), fg=colors.get("console_text", "#d7ffe4"), relief="flat", wrap="word", padx=10, pady=10)
        note.pack(fill="both", expand=True, pady=(4, 0))
        note.insert("1.0", self._notes_text())
        note.configure(state="disabled")

    def _button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", bd=0, padx=12, pady=8, cursor="hand2", font=("Segoe UI", 9, "bold"))

    def _status_text(self) -> str:
        if not HOUSEKEEPING_DIR.exists():
            return f"Missing housekeeping folder: {HOUSEKEEPING_DIR}"
        summary = _latest_file(HOUSEKEEPING_DIR / "summaries", "housekeeping-summary-*.md")
        report = _latest_file(HOUSEKEEPING_DIR / "reports", "housekeeping-report-*.md")
        manifest = HOUSEKEEPING_DIR / "manifests" / "latest_apply_manifest.json"
        parts = [f"Housekeeping folder: {HOUSEKEEPING_DIR}"]
        parts.append(f"Latest summary: {summary.name if summary else 'none yet'}")
        parts.append(f"Latest report: {report.name if report else 'none yet'}")
        parts.append(f"Latest apply manifest: {'yes' if manifest.exists() else 'none yet'}")
        return "\n".join(parts)

    def _notes_text(self) -> str:
        return (
            "Normal flow:\n"
            "1. Open Housekeeping Console.\n"
            "2. Preview Full Run.\n"
            "3. Review the short summary.\n"
            "4. Approve + Apply only when it looks sane.\n"
            "5. Use Undo Last Applied Run before making unrelated edits if something looks wrong.\n\n"
            "This plugin intentionally launches the existing housekeeping UI instead of rewriting it inside the toolbox. "
            "That keeps the saved-plan/apply/undo safety model intact."
        )

    def validate(self, host):
        if HOUSEKEEPING_DIR.exists() and HOUSEKEEPING_UI.exists():
            host.log("Housekeeping Console: validation OK")
        else:
            host.error(f"Housekeeping Console missing: {HOUSEKEEPING_UI}")


class HousekeepingConsoleTool(BaseTool):
    """Legacy BaseTool compatibility wrapper."""

    def __init__(self):
        self.cancel_requested = False
        try:
            self.reset_run_state()
        except Exception:
            pass

    def get_name(self):
        return "ðŸ§¹ Housekeeping Console"

    def build_ui(self, parent_frame):
        tk.Label(parent_frame, text="Housekeeping Console", bg="#121a2b", fg="#edf3ff", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(parent_frame, text="Use Queue Execute to open the housekeeping UI, or use the buttons below.", bg="#121a2b", fg="#8ea2c7", wraplength=420, justify="left").pack(anchor="w", pady=(4, 10))
        tk.Button(parent_frame, text="Open Housekeeping Console", command=_launch_housekeeping, bg="#4ecdc4", fg="#08111e", relief="flat", padx=12, pady=8).pack(anchor="w", pady=(0, 8))
        tk.Button(parent_frame, text="Open Housekeeping Folder", command=lambda: _open_path(HOUSEKEEPING_DIR), bg="#202d45", fg="#edf3ff", relief="flat", padx=12, pady=8).pack(anchor="w")

    def execute(self, target_path, is_live, log_callback, progress_callback):
        log_callback("Opening QiLabs Housekeeping Console...")
        _launch_housekeeping()
        progress_callback(100)