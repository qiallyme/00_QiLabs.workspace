#!/usr/bin/env python3
"""
QiLabs BAT Launcher
Scans C:\\QiLabs for .bat files, builds a registry, and provides a click-to-run UI.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tkinter import Tk, StringVar, BooleanVar, END, BOTH, LEFT, RIGHT, X, Y, NSEW, filedialog, messagebox
from tkinter import ttk
import tkinter as tk

APP_NAME = "QiLabs BAT Launcher"
TOOL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TOOL_DIR / "bat_launcher.config.json"
REGISTRY_PATH = TOOL_DIR / "bat_registry.json"
LOG_DIR = TOOL_DIR / "logs"
LOG_PATH = LOG_DIR / "bat_launcher_runs.jsonl"

DEFAULT_CONFIG = {
    "schema_version": "1.0",
    "scan_roots": ["C:\\QiLabs"],
    "include_extensions": [".bat"],
    "include_cmd_files": False,
    "confirm_before_run": True,
    "open_in_new_console": True,
    "keep_console_open": True,
    "max_preview_lines": 120,
    "exclude_dir_names": [
        ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__",
        "dist", "build", ".next", ".turbo", ".cache", "site-packages", "$Recycle.Bin",
        "System Volume Information", "Windows", "Program Files", "Program Files (x86)", "ProgramData",
        "AppData", "Microsoft", "OneDriveTemp"
    ],
    "exclude_path_contains": [
        "\\Windows\\", "\\Program Files\\", "\\Program Files (x86)\\", "\\ProgramData\\", "\\AppData\\",
        "\\node_modules\\", "\\.git\\", "\\.venv\\", "\\venv\\", "\\__pycache__\\"
    ],
    "high_risk_patterns": [
        "format ", "diskpart", "bcdedit", "reg delete", "shutdown ", "cipher /w", "takeown ",
        "icacls ", "del /s", "erase /s", "rmdir /s", "rd /s", "remove-item", "powershell -enc",
        "set-executionpolicy", "net user", "sc delete", "schtasks /delete"
    ],
    "metadata_patterns": {
        "title": [r"^\s*(?:rem|::)\s*(?:tool|title|name)\s*:\s*(.+)$"],
        "description": [r"^\s*(?:rem|::)\s*(?:description|desc|summary)\s*:\s*(.+)$"],
        "category": [r"^\s*(?:rem|::)\s*(?:category|group)\s*:\s*(.+)$"],
        "safe": [r"^\s*(?:rem|::)\s*(?:safe|risk)\s*:\s*(.+)$"]
    }
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_json(CONFIG_PATH, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as exc:
        messagebox.showwarning(APP_NAME, f"Config could not be read. Using defaults.\n\n{exc}")
        config = dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    # If user enables .cmd files, include them dynamically.
    exts = set(e.lower() for e in merged.get("include_extensions", [".bat"]))
    if merged.get("include_cmd_files"):
        exts.add(".cmd")
    merged["include_extensions"] = sorted(exts)
    return merged


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def normcase_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def should_skip_dir(dir_path: Path, config: dict) -> bool:
    if dir_path.name in set(config.get("exclude_dir_names", [])):
        return True
    s = "\\" + str(dir_path.resolve()).replace("/", "\\") + "\\"
    for needle in config.get("exclude_path_contains", []):
        if needle.lower() in s.lower():
            return True
    return False


def read_text_preview(path: Path, max_lines: int = 120) -> tuple[str, list[str]]:
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.rstrip("\n"))
    except Exception as exc:
        return f"[Could not read preview: {exc}]", []
    return "\n".join(lines), lines


def extract_metadata(path: Path, config: dict) -> dict:
    preview, lines = read_text_preview(path, max_lines=60)
    metadata = {
        "title": path.stem,
        "description": "",
        "category": path.parent.name,
        "safe": "unknown"
    }
    patterns = config.get("metadata_patterns", {})
    for key, pats in patterns.items():
        for line in lines[:40]:
            for pat in pats:
                m = re.search(pat, line, flags=re.IGNORECASE)
                if m:
                    metadata[key] = m.group(1).strip()
                    break
            if metadata.get(key) and metadata.get(key) != DEFAULT_CONFIG["metadata_patterns"].get(key):
                # continue outer loop only if a match actually set the field
                pass
    if not metadata.get("description"):
        # Grab the first useful comment line as fallback.
        for line in lines[:20]:
            stripped = line.strip()
            if stripped.lower().startswith("rem "):
                metadata["description"] = stripped[4:].strip()
                break
            if stripped.startswith("::"):
                metadata["description"] = stripped[2:].strip()
                break
    metadata["preview"] = preview
    return metadata


def classify_risk(path: Path, config: dict) -> tuple[str, list[str]]:
    preview, _ = read_text_preview(path, max_lines=200)
    lower = preview.lower()
    hits = []
    for pattern in config.get("high_risk_patterns", []):
        if pattern.lower() in lower:
            hits.append(pattern)
    if hits:
        return "review", hits
    return "normal", []


def scan_bat_files(config: dict) -> dict:
    roots = [Path(p) for p in config.get("scan_roots", ["C:\\QiLabs"])]
    exts = set(e.lower() for e in config.get("include_extensions", [".bat"]))
    records = []
    skipped_roots = []

    for root in roots:
        if not root.exists():
            skipped_roots.append(str(root))
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not should_skip_dir(current / d, config)]
            for filename in filenames:
                p = current / filename
                if p.suffix.lower() not in exts:
                    continue
                if not any(is_under(p, r) for r in roots if r.exists()):
                    continue
                # Hard QiLabs-only guard.
                if "qilabs" not in normcase_path(p):
                    continue
                stat = p.stat()
                meta = extract_metadata(p, config)
                risk, hits = classify_risk(p, config)
                root_match = next((r for r in roots if r.exists() and is_under(p, r)), root)
                records.append({
                    "id": str(abs(hash(normcase_path(p)))),
                    "name": p.name,
                    "title": meta.get("title") or p.stem,
                    "description": meta.get("description") or "",
                    "category": meta.get("category") or p.parent.name,
                    "path": str(p),
                    "relative_path": str(p.relative_to(root_match)) if is_under(p, root_match) else str(p),
                    "folder": str(p.parent),
                    "modified": dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(),
                    "size_bytes": stat.st_size,
                    "risk": risk,
                    "risk_hits": hits,
                    "preview": meta.get("preview", "")
                })

    records.sort(key=lambda r: (r["category"].lower(), r["title"].lower(), r["relative_path"].lower()))
    registry = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "app": APP_NAME,
        "scan_roots": [str(r) for r in roots],
        "skipped_roots": skipped_roots,
        "count": len(records),
        "bat_files": records
    }
    save_json(REGISTRY_PATH, registry)
    return registry


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            with REGISTRY_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"bat_files": [], "count": 0, "generated_at": "never"}


def append_log(event: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["timestamp"] = now_iso()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_bat(record: dict, config: dict) -> None:
    path = Path(record["path"])
    roots = [Path(p) for p in config.get("scan_roots", ["C:\\QiLabs"]) if Path(p).exists()]
    if not path.exists():
        raise FileNotFoundError(f"BAT file no longer exists: {path}")
    if path.suffix.lower() not in set(config.get("include_extensions", [".bat"])):
        raise ValueError(f"Refusing to run non-allowed file extension: {path.suffix}")
    if not roots or not any(is_under(path, root) for root in roots):
        raise ValueError("Refusing to run file outside configured QiLabs scan roots.")

    append_log({"event": "run_requested", "path": str(path), "risk": record.get("risk"), "title": record.get("title")})

    quoted_parent = str(path.parent)
    quoted_path = str(path)
    if sys.platform.startswith("win"):
        if config.get("open_in_new_console", True):
            if config.get("keep_console_open", True):
                command = f'cd /d "{quoted_parent}" && call "{quoted_path}"'
                subprocess.Popen(["cmd.exe", "/c", "start", "", "cmd.exe", "/k", command])
            else:
                command = f'cd /d "{quoted_parent}" && call "{quoted_path}"'
                subprocess.Popen(["cmd.exe", "/c", "start", "", "cmd.exe", "/c", command])
        else:
            subprocess.Popen(["cmd.exe", "/c", "call", quoted_path], cwd=str(path.parent))
    else:
        raise RuntimeError("This launcher is designed for Windows .bat files.")

    append_log({"event": "run_launched", "path": str(path), "risk": record.get("risk"), "title": record.get("title")})


class BatLauncherApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1180x760")
        self.config = load_config()
        self.registry = load_registry()
        self.records: list[dict] = self.registry.get("bat_files", [])
        self.filtered_records: list[dict] = []
        self.search_var = StringVar()
        self.status_var = StringVar(value="Ready.")
        self.confirm_var = BooleanVar(value=bool(self.config.get("confirm_before_run", True)))
        self.include_cmd_var = BooleanVar(value=bool(self.config.get("include_cmd_files", False)))
        self._build_ui()
        self.apply_filter()
        if not self.records:
            self.refresh_registry()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, padx=(0, 6))
        search = ttk.Entry(top, textvariable=self.search_var)
        search.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        search.bind("<KeyRelease>", lambda _e: self.apply_filter())

        ttk.Button(top, text="Refresh BAT Registry", command=self.refresh_registry).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Run Selected", command=self.run_selected).grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Open Folder", command=self.open_folder).grid(row=0, column=4, padx=4)
        ttk.Button(top, text="Copy Path", command=self.copy_path).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="Open Registry", command=self.open_registry).grid(row=0, column=6, padx=4)

        opts = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        opts.grid(row=1, column=0, sticky="ew")
        ttk.Checkbutton(opts, text="Confirm before run", variable=self.confirm_var).pack(side=LEFT, padx=(0, 14))
        ttk.Checkbutton(opts, text="Include .cmd files on refresh", variable=self.include_cmd_var, command=self.toggle_cmd_files).pack(side=LEFT, padx=(0, 14))
        ttk.Label(opts, text="Tip: add comments like `REM Tool: Name` and `REM Description: ...` at the top of BAT files for nicer labels.").pack(side=LEFT)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.grid(row=2, column=0, sticky=NSEW, padx=10, pady=(0, 10))

        left = ttk.Frame(main)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        columns = ("title", "category", "relative_path", "modified", "risk")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, text, width in [
            ("title", "Tool", 220),
            ("category", "Category", 130),
            ("relative_path", "Relative Path", 420),
            ("modified", "Modified", 155),
            ("risk", "Risk", 80),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky=NSEW)
        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_selected_details())
        self.tree.bind("<Double-1>", lambda _e: self.run_selected())
        main.add(left, weight=3)

        right = ttk.Frame(main, padding=(8, 0, 0, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="Details / Preview").grid(row=0, column=0, sticky="w")
        self.preview = tk.Text(right, wrap="none", height=20)
        self.preview.grid(row=1, column=0, sticky=NSEW)
        py = ttk.Scrollbar(right, orient="vertical", command=self.preview.yview)
        py.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=py.set)
        main.add(right, weight=2)

        bottom = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.status = ttk.Label(bottom, textvariable=self.status_var)
        self.status.grid(row=0, column=0, sticky="w")

    def toggle_cmd_files(self):
        self.config["include_cmd_files"] = bool(self.include_cmd_var.get())
        save_json(CONFIG_PATH, self.config)
        self.config = load_config()

    def refresh_registry(self):
        try:
            self.status_var.set("Scanning C:\\QiLabs for BAT files...")
            self.root.update_idletasks()
            self.config["include_cmd_files"] = bool(self.include_cmd_var.get())
            save_json(CONFIG_PATH, self.config)
            self.config = load_config()
            self.registry = scan_bat_files(self.config)
            self.records = self.registry.get("bat_files", [])
            self.apply_filter()
            self.status_var.set(f"Registry refreshed: {len(self.records)} BAT tool(s). Saved to {REGISTRY_PATH}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Scan failed:\n\n{exc}")
            self.status_var.set("Scan failed.")

    def apply_filter(self):
        query = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.filtered_records = []
        for rec in self.records:
            blob = " ".join(str(rec.get(k, "")) for k in ["title", "name", "description", "category", "relative_path", "path", "risk"]).lower()
            if query and query not in blob:
                continue
            self.filtered_records.append(rec)
            self.tree.insert("", END, iid=rec["id"], values=(
                rec.get("title", rec.get("name", "")),
                rec.get("category", ""),
                rec.get("relative_path", ""),
                rec.get("modified", ""),
                rec.get("risk", ""),
            ))
        self.status_var.set(f"Showing {len(self.filtered_records)} of {len(self.records)} BAT tool(s). Registry generated: {self.registry.get('generated_at', 'never')}")

    def selected_record(self) -> dict | None:
        sel = self.tree.selection()
        if not sel:
            return None
        selected_id = sel[0]
        return next((r for r in self.records if r.get("id") == selected_id), None)

    def show_selected_details(self):
        rec = self.selected_record()
        self.preview.delete("1.0", END)
        if not rec:
            return
        details = [
            f"Tool: {rec.get('title')}",
            f"Path: {rec.get('path')}",
            f"Category: {rec.get('category')}",
            f"Modified: {rec.get('modified')}",
            f"Risk: {rec.get('risk')}",
            f"Risk hits: {', '.join(rec.get('risk_hits') or []) or 'none'}",
            f"Description: {rec.get('description') or '—'}",
            "",
            "--- BAT Preview ---",
            rec.get("preview", "")
        ]
        self.preview.insert("1.0", "\n".join(details))

    def run_selected(self):
        rec = self.selected_record()
        if not rec:
            messagebox.showinfo(APP_NAME, "Select a BAT file first.")
            return
        warning = ""
        if rec.get("risk") != "normal":
            warning = "\n\nRisk markers detected:\n- " + "\n- ".join(rec.get("risk_hits") or ["review required"])
        if self.confirm_var.get():
            ok = messagebox.askyesno(APP_NAME, f"Run this BAT file in a new console?\n\n{rec.get('title')}\n{rec.get('path')}{warning}")
            if not ok:
                self.status_var.set("Run cancelled.")
                return
        try:
            run_bat(rec, self.config)
            self.status_var.set(f"Launched: {rec.get('title')}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not run BAT file:\n\n{exc}")
            self.status_var.set("Run failed.")

    def open_folder(self):
        rec = self.selected_record()
        if not rec:
            return
        folder = Path(rec["folder"])
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(folder)])
        else:
            messagebox.showinfo(APP_NAME, str(folder))

    def copy_path(self):
        rec = self.selected_record()
        if not rec:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(rec["path"])
        self.status_var.set("Path copied to clipboard.")

    def open_registry(self):
        if not REGISTRY_PATH.exists():
            self.refresh_registry()
        if sys.platform.startswith("win"):
            subprocess.Popen(["notepad", str(REGISTRY_PATH)])
        else:
            messagebox.showinfo(APP_NAME, str(REGISTRY_PATH))


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = BatLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
