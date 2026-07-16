#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive GUI wrapper for safe_qivault_empower_migrator.py
Double-click launcher. No command-line use required.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import safe_qivault_empower_migrator as mig
except Exception as e:
    raise RuntimeError(f"Could not load safe_qivault_empower_migrator.py from {HERE}: {e}")

DEFAULT_TARGET = r"C:\QiLabs\40_QiVault\30_empowerqnow713"
DEFAULT_TEMPLATE = str(HERE / "master_template.md")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QiVault EmpowerQNow713 Interactive Migrator")
        self.geometry("980x720")
        self.minsize(860, 620)
        self.running = False
        self.root_var = tk.StringVar(value=DEFAULT_TARGET)
        self.template_var = tk.StringVar(value=DEFAULT_TEMPLATE if Path(DEFAULT_TEMPLATE).exists() else "")
        self.index_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready. Start with Dry Run. Then Safe Copy. Move is danger zone.")
        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="QiVault EmpowerQNow713 Interactive Migrator", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="No command line. Safe defaults: dry-run first, copy before move, never overwrite.").pack(anchor="w", pady=(2, 14))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Target folder", width=16).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.root_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Choose...", command=self.choose_root).pack(side=tk.LEFT, padx=(8, 0))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Master template", width=16).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.template_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Choose...", command=self.choose_template).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Checkbutton(frame, text="Create missing _index.md files from master template", variable=self.index_var).pack(anchor="w", pady=(8, 12))

        ttk.Label(
            frame,
            text="Correct order: 1) Dry Run → 2) Safe Copy → verify in Obsidian → only then consider Move.",
            foreground="#9a3412",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(buttons, text="1) DRY RUN / Preview Only", command=lambda: self.run_task(False, "copy")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="2) SAFE COPY Migration", command=lambda: self.confirm_copy()).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="3) MOVE Originals (Danger Zone)", command=lambda: self.confirm_move()).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Open Logs Folder", command=self.open_logs).pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(0, 4))

        self.output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9))
        self.output.pack(fill=tk.BOTH, expand=True)

    def choose_root(self):
        folder = filedialog.askdirectory(title="Choose the 30_empowerqnow713 folder")
        if folder:
            self.root_var.set(folder)

    def choose_template(self):
        file = filedialog.askopenfilename(title="Choose master_template.md", filetypes=[("Markdown", "*.md"), ("All files", "*.*")])
        if file:
            self.template_var.set(file)

    def log(self, msg=""):
        self.output.insert(tk.END, str(msg) + "\n")
        self.output.see(tk.END)
        self.update_idletasks()

    def validate_root(self):
        root = Path(self.root_var.get()).expanduser()
        if not root.exists() or not root.is_dir():
            messagebox.showerror("Bad target folder", f"This folder does not exist:\n\n{root}")
            return None
        if root.name.lower() != "30_empowerqnow713":
            messagebox.showerror(
                "Safety stop",
                "This tool only runs on a folder named 30_empowerqnow713.\n\n"
                f"You selected:\n{root}\n\nPick the exact writing section folder."
            )
            return None
        return root.resolve()

    def get_template_text(self):
        p = Path(self.template_var.get()).expanduser() if self.template_var.get().strip() else None
        if p and p.exists() and p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
        return mig.DEFAULT_MASTER_TEMPLATE

    def confirm_copy(self):
        ok = messagebox.askyesno(
            "Safe Copy Migration",
            "This will create the clean folder structure and COPY files into it.\n\n"
            "Original files stay where they are.\n\nContinue?"
        )
        if ok:
            self.run_task(True, "copy")

    def confirm_move(self):
        ok = messagebox.askyesno(
            "MOVE mode warning",
            "MOVE mode changes the original folder layout.\n\n"
            "Do NOT use this until the Safe Copy result is verified.\n\nContinue anyway?"
        )
        if ok:
            self.run_task(True, "move")

    def run_task(self, apply, mode):
        if self.running:
            messagebox.showinfo("Already running", "A migration is already running.")
            return
        root = self.validate_root()
        if root is None:
            return
        self.running = True
        self.output.delete("1.0", tk.END)
        self.progress.start(10)
        self.status_var.set("Running...")

        def worker():
            try:
                template = self.get_template_text()
                self.after(0, lambda: self._run_inside(root, template, apply, mode))
            except Exception as e:
                tb = traceback.format_exc()
                self.after(0, lambda: self.log(tb))
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_var.set("Error. See log."))
            finally:
                self.after(0, self.progress.stop)
                self.running = False
        threading.Thread(target=worker, daemon=True).start()

    def _run_inside(self, root, template, apply, mode):
        self.log(f"Target: {root}")
        self.log(f"Mode: {mode}")
        self.log(f"Apply changes: {apply}")
        self.log("")

        rows = mig.build_plan(root)
        self.log(f"Files found/classified: {len(rows)}")
        self.log("")

        # Capture prints from the underlying safe script so they do not require a command prompt.
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            dir_log = mig.create_dirs_and_indexes(root, template, apply=apply, make_indexes=self.index_var.get())
            rows = mig.apply_plan(rows, root=root, mode=mode, apply=apply)
            if apply:
                mig.write_logs(root, rows, dir_log, apply=apply)

        counts = {}
        for row in rows:
            counts[row.status] = counts.get(row.status, 0) + 1

        # Dry-run preview with no file changes.
        if not apply:
            self.log("DRY RUN PREVIEW — no files changed")
            preview_limit = 250
            shown = 0
            for row in rows:
                if row.action in {"move", "review"}:
                    src = row.source.relative_to(root)
                    dst = row.final_destination.relative_to(root) if row.final_destination and str(row.final_destination).startswith(str(root)) else row.final_destination
                    self.log(f"WOULD {mode.upper()}: {src} -> {dst} | {row.reason}")
                    shown += 1
                    if shown >= preview_limit:
                        self.log(f"...preview capped at {preview_limit} rows. Full applied run will write CSV logs.")
                        break
        else:
            self.log(captured.getvalue().strip())

        self.log("")
        self.log("Summary:")
        for k, v in sorted(counts.items()):
            self.log(f"  {k}: {v}")

        log_dir = root / "00_system" / "migration_logs"
        if apply:
            self.log("")
            self.log(f"Logs written to: {log_dir}")
        self.status_var.set("Done.")
        messagebox.showinfo("Done", "Migration task finished. Review the output and logs.")

    def open_logs(self):
        root = self.validate_root()
        if root is None:
            return
        log_dir = root / "00_system" / "migration_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(log_dir))
        except Exception as e:
            messagebox.showerror("Could not open logs", str(e))

if __name__ == "__main__":
    App().mainloop()
