from __future__ import annotations

import importlib
import json
import os
import queue
import sys
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context import RunContext

CONFIG_PATH = ROOT / "housekeeping_config.json"

# Full run is the normal path: preview the full safe housekeeping plan, then approve/apply that exact saved plan.
FULL_PREVIEW_STEPS = [
    "preflight",
    "validate_tags",
    "validate_templates",
    "scan_inventory",
    "normalize_frontmatter",
    "plan_filename_normalization",
    "rewrite_links",
    "rebuild_indexes",
    "update_full_tree",
    "update_git_manifest",
    "generate_report",
]

# Git is intentionally not part of the saved file-mutation plan. It is run live after apply because commit/push must see
# the actual working tree after the saved plan has been applied.
APPLY_STEPS_BASE = ["apply_saved_plan", "generate_report"]
UNDO_STEPS = ["undo_last_run", "generate_report"]

MANUAL_STEPS = [
    ("preflight", "Preflight"),
    ("validate_tags", "Validate tags"),
    ("validate_templates", "Validate master template"),
    ("scan_inventory", "Scan inventory"),
    ("normalize_frontmatter", "Normalize frontmatter"),
    ("plan_filename_normalization", "Plan filename normalization"),
    ("rewrite_links", "Rewrite links from rename map"),
    ("rebuild_indexes", "Rebuild folder indexes"),
    ("update_full_tree", "Update QiLabs full tree"),
    ("update_git_manifest", "Update Git manifest"),
    ("generate_report", "Generate report"),
    ("git_commit_push", "Recursive Git commit / push"),
]

LABEL_BY_MODULE = dict(MANUAL_STEPS) | {
    "apply_saved_plan": "Apply saved approval plan",
    "undo_last_run": "Undo last applied run",
}


class HousekeepingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QiLabs Housekeeping Console")
        self.geometry("1220x820")
        self.minsize(1020, 680)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.current_thread: threading.Thread | None = None

        self.include_renames_var = tk.BooleanVar(value=False)
        self.commit_after_apply_var = tk.BooleanVar(value=True)
        self.push_after_commit_var = tk.BooleanVar(value=False)

        self.full_plan_file: Path | None = None
        self.manual_plan_file: Path | None = None
        self.last_summary_file: Path | None = None
        self.manual_step_var = tk.StringVar(value=MANUAL_STEPS[0][1])

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self._refresh_latest_manifest_summary()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="QiLabs Housekeeping Console", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="Normal flow: preview full plan → review short summary → approve/apply saved plan → optional one-click undo. Manual mode is for one-off surgery."
        )
        subtitle.pack(anchor="w", pady=(2, 10))

        top = ttk.Frame(outer)
        top.pack(fill="x")

        full = ttk.LabelFrame(top, text="Full Run Workflow", padding=10)
        full.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(full, text="Use this 95% of the time. It saves an approval plan, then applies that exact plan without rescanning.").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Checkbutton(full, text="Include filename renames in plan", variable=self.include_renames_var).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(full, text="Commit after apply", variable=self.commit_after_apply_var).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Checkbutton(full, text="Push after commit", variable=self.push_after_commit_var).grid(row=1, column=2, sticky="w", pady=2)

        ttk.Button(full, text="1. Preview Full Run", command=self.preview_full_run).grid(row=2, column=0, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(full, text="2. Approve + Apply", command=self.approve_full_plan).grid(row=2, column=1, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(full, text="Undo Last Applied Run", command=self.undo_last_applied_run).grid(row=2, column=2, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(full, text="Cancel Preview", command=self.cancel_full_plan).grid(row=2, column=3, sticky="ew", padx=4, pady=(8, 4))
        for i in range(4):
            full.columnconfigure(i, weight=1)

        self.full_plan_label = ttk.Label(full, text="No full-run preview plan loaded.", foreground="#555")
        self.full_plan_label.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        manual = ttk.LabelFrame(top, text="Manual Step Mode", padding=10)
        manual.pack(side="left", fill="both", expand=True)

        ttk.Label(manual, text="Use this when you only want one step previewed/applied.").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.manual_combo = ttk.Combobox(manual, textvariable=self.manual_step_var, values=[label for _m, label in MANUAL_STEPS], state="readonly")
        self.manual_combo.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=2)
        ttk.Button(manual, text="Preview Step", command=self.preview_manual_step).grid(row=2, column=0, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(manual, text="Approve Step Plan", command=self.approve_manual_plan).grid(row=2, column=1, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(manual, text="Cancel Step", command=self.cancel_manual_plan).grid(row=2, column=2, sticky="ew", padx=4, pady=(8, 4))
        for i in range(3):
            manual.columnconfigure(i, weight=1)

        self.manual_plan_label = ttk.Label(manual, text="No manual step preview plan loaded.", foreground="#555")
        self.manual_plan_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        summary_frame = ttk.LabelFrame(outer, text="Short Run Summary", padding=8)
        summary_frame.pack(fill="x", pady=(10, 0))
        self.summary_text = tk.Text(summary_frame, wrap="word", height=8, font=("Consolas", 10))
        self.summary_text.pack(side="left", fill="both", expand=True)
        summary_buttons = ttk.Frame(summary_frame)
        summary_buttons.pack(side="right", fill="y", padx=(8, 0))
        ttk.Button(summary_buttons, text="Open Summary", command=self.open_last_summary).pack(fill="x", pady=2)
        ttk.Button(summary_buttons, text="Open Reports Folder", command=lambda: self._open_path(ROOT / "reports")).pack(fill="x", pady=2)
        ttk.Button(summary_buttons, text="Open Manifests Folder", command=lambda: self._open_path(ROOT / "manifests")).pack(fill="x", pady=2)
        ttk.Button(summary_buttons, text="Refresh", command=self._refresh_latest_manifest_summary).pack(fill="x", pady=2)

        rightbar = ttk.Frame(outer)
        rightbar.pack(fill="x", pady=(10, 0))
        ttk.Button(rightbar, text="Clear Log", command=self.clear_log).pack(side="right")

        out_frame = ttk.LabelFrame(outer, text="Verbose Output", padding=8)
        out_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.output = tk.Text(out_frame, wrap="word", height=24, font=("Consolas", 10))
        yscroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=yscroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self.status = ttk.Label(outer, text=f"Config: {CONFIG_PATH}", anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

    def screen_log(self, message: str):
        self.log_queue.put(message)

    def _drain_log_queue(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.output.insert("end", msg + "\n")
            self.output.see("end")
        self.after(100, self._drain_log_queue)

    def clear_log(self):
        self.output.delete("1.0", "end")

    def _busy(self) -> bool:
        if self.current_thread and self.current_thread.is_alive():
            messagebox.showwarning("Run active", "A housekeeping run is already active.")
            return True
        return False

    def _selected_manual_module(self) -> str:
        label = self.manual_step_var.get()
        for module, module_label in MANUAL_STEPS:
            if module_label == label:
                return module
        return MANUAL_STEPS[0][0]

    def _open_path(self, path: Path | str | None):
        if not path:
            messagebox.showinfo("Nothing to open", "No file/folder is available yet.")
            return
        p = Path(path)
        if not p.exists():
            messagebox.showwarning("Missing", f"Path does not exist:\n{p}")
            return
        try:
            os.startfile(str(p))  # Windows
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))

    def open_last_summary(self):
        self._open_path(self.last_summary_file)

    def _set_summary_text(self, text: str):
        def update():
            self.summary_text.delete("1.0", "end")
            self.summary_text.insert("end", text)
        self.after(0, update)

    def _summary_from_plan(self, plan_file: Path) -> str:
        try:
            data = json.loads(Path(plan_file).read_text(encoding="utf-8"))
            actions = data.get("actions", [])
            warnings = data.get("warnings", [])
            errors = data.get("errors", [])
            writes = sum(1 for a in actions if a.get("type") == "write_text")
            renames = sum(1 for a in actions if a.get("type") == "rename")
            status = "Needs review" if errors else ("Completed with warnings" if warnings else "Ready to approve")
            report = data.get("report_file", "")
            self.last_summary_file = Path(report) if report else None
            lines = [
                f"Status: {status}",
                f"Preview run: {data.get('run_id')}",
                f"Plan kind: {data.get('plan_kind')}",
                f"Actions planned: {len(actions)}  | Writes: {writes}  | Renames: {renames}",
                f"Warnings: {len(warnings)}  | Errors: {len(errors)}",
                f"Plan: {plan_file}",
                f"Report: {report}",
            ]
            if warnings:
                lines.append("Top warning: " + str(warnings[0])[:220])
            if errors:
                lines.append("Top error: " + str(errors[0])[:220])
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not summarize plan: {exc}\nPlan: {plan_file}"

    def _summary_from_ctx(self, ctx: RunContext) -> str:
        s = ctx.state.get("run_summary", {})
        if not s:
            return f"Run complete: {ctx.run_id}\nReport: {ctx.report_file}"
        self.last_summary_file = Path(s.get("summary_file") or ctx.summary_file)
        lines = [
            f"Status: {s.get('status')}",
            f"Run: {s.get('run_id')}  | Mode: {s.get('mode')}",
            f"Planned: {s.get('planned_actions')}  | Writes: {s.get('planned_writes')}  | Renames: {s.get('planned_renames')}",
            f"Applied: {s.get('applied_actions')}  | Skipped: {s.get('skipped_actions')}  | Changed files: {s.get('changed_files')}",
            f"Warnings: {s.get('warnings')}  | Errors: {s.get('errors')}",
            f"Summary: {s.get('summary_file')}",
            f"Report: {s.get('report_file')}",
        ]
        if s.get("apply_manifest_file"):
            lines.append(f"Undo source manifest: {s.get('apply_manifest_file')}")
        if s.get("undo_manifest_file"):
            lines.append(f"Undo manifest: {s.get('undo_manifest_file')}")
        return "\n".join(lines)

    def _refresh_latest_manifest_summary(self):
        pointer = ROOT / "manifests" / "latest_apply_manifest.json"
        if not pointer.exists():
            self._set_summary_text("No applied run manifest yet. First run will create one after Approve + Apply.")
            return
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            self._set_summary_text(
                "Latest applied run manifest\n"
                f"Run: {data.get('apply_run_id')}\n"
                f"Created: {data.get('created_at')}\n"
                f"Manifest: {data.get('latest_apply_manifest')}\n"
                f"Summary: {json.dumps(data.get('summary', {}), indent=2)}"
            )
        except Exception as exc:
            self._set_summary_text(f"Could not read latest manifest pointer: {exc}")

    def preview_full_run(self):
        if self._busy():
            return
        self.full_plan_file = None
        self.full_plan_label.configure(text="Building full-run preview plan...")
        self._start_worker(
            target=self._worker_preview,
            modules=FULL_PREVIEW_STEPS,
            plan_kind="full",
            allow_renames=self.include_renames_var.get(),
            on_done="full_preview",
        )

    def approve_full_plan(self):
        if self._busy():
            return
        if not self.full_plan_file or not self.full_plan_file.exists():
            messagebox.showwarning("No full-run plan", "Run Preview Full Run first, then approve it.")
            return
        msg = f"Apply the saved full-run plan?\n\n{self.full_plan_file}\n\nThis does not rescan. It applies the exact file actions from the preview."
        if not messagebox.askyesno("Approve saved plan", msg):
            return
        modules = APPLY_STEPS_BASE.copy()
        if self.commit_after_apply_var.get():
            modules.append("git_commit_push")
        self._start_worker(
            target=self._worker_apply_plan,
            modules=modules,
            plan_file=self.full_plan_file,
            allow_renames=self.include_renames_var.get(),
            push=self.push_after_commit_var.get(),
            on_done="full_apply",
        )

    def undo_last_applied_run(self):
        if self._busy():
            return
        pointer = ROOT / "manifests" / "latest_apply_manifest.json"
        if not pointer.exists():
            messagebox.showinfo("No manifest", "There is no applied run manifest to undo yet.")
            return
        if not messagebox.askyesno(
            "Undo last applied run",
            "Undo the last applied housekeeping run?\n\nChanged/moved files are skipped safely and logged. Git commits/pushes are not auto-reversed."
        ):
            return
        self._start_worker(target=self._worker_undo_last_run, modules=UNDO_STEPS)

    def cancel_full_plan(self):
        self.full_plan_file = None
        self.full_plan_label.configure(text="Full-run preview canceled. No saved plan loaded.")
        self.screen_log("[INFO] Full-run preview plan canceled in UI. No files changed.")

    def preview_manual_step(self):
        if self._busy():
            return
        module = self._selected_manual_module()
        self.manual_plan_file = None
        self.manual_plan_label.configure(text=f"Building manual preview for: {LABEL_BY_MODULE.get(module, module)}")
        self._start_worker(
            target=self._worker_preview,
            modules=[module],
            plan_kind="manual",
            allow_renames=self.include_renames_var.get(),
            on_done="manual_preview",
        )

    def approve_manual_plan(self):
        if self._busy():
            return
        if not self.manual_plan_file or not self.manual_plan_file.exists():
            messagebox.showwarning("No manual plan", "Run Preview Step first, then approve it.")
            return
        msg = f"Apply this saved manual step plan?\n\n{self.manual_plan_file}\n\nThis applies the exact file actions from that step preview."
        if not messagebox.askyesno("Approve manual step plan", msg):
            return
        self._start_worker(
            target=self._worker_apply_plan,
            modules=APPLY_STEPS_BASE.copy(),
            plan_file=self.manual_plan_file,
            allow_renames=self.include_renames_var.get(),
            push=False,
            on_done="manual_apply",
        )

    def cancel_manual_plan(self):
        self.manual_plan_file = None
        self.manual_plan_label.configure(text="Manual step preview canceled. No saved plan loaded.")
        self.screen_log("[INFO] Manual preview plan canceled in UI. No files changed.")

    def _start_worker(self, target, **kwargs):
        self.status.configure(text="Running...")
        self.current_thread = threading.Thread(target=target, kwargs=kwargs, daemon=True)
        self.current_thread.start()

    def _worker_preview(self, modules: list[str], plan_kind: str, allow_renames: bool, on_done: str):
        ctx = RunContext(CONFIG_PATH, dry_run=True, allow_renames=allow_renames, push=False, screen_log=self.screen_log)
        self._log_run_header(ctx, modules, "PREVIEW")
        try:
            self._run_modules(ctx, modules)
            plan_file = ctx.save_plan(modules=modules, plan_kind=plan_kind)
            self.screen_log("")
            self.screen_log(f"Preview done. Approval plan: {plan_file}")
            self.screen_log(f"Summary: {ctx.summary_file}")
            self.screen_log(f"Report: {ctx.report_file}")
            self._set_summary_text(self._summary_from_plan(plan_file))
            if on_done == "full_preview":
                self.full_plan_file = plan_file
                self.after(0, lambda: self.full_plan_label.configure(text=f"Ready to approve: {plan_file}"))
            elif on_done == "manual_preview":
                self.manual_plan_file = plan_file
                self.after(0, lambda: self.manual_plan_label.configure(text=f"Ready to approve: {plan_file}"))
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled preview error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(text=f"Last preview: {ctx.run_id} | Plan: {ctx.plan_file}"))

    def _worker_apply_plan(self, modules: list[str], plan_file: Path, allow_renames: bool, push: bool, on_done: str):
        ctx = RunContext(CONFIG_PATH, dry_run=False, allow_renames=allow_renames, push=push, screen_log=self.screen_log)
        ctx.state["approval_plan_file"] = str(plan_file)
        self._log_run_header(ctx, modules, "APPLY SAVED PLAN")
        self.screen_log(f"Applying saved plan without rescanning: {plan_file}")
        try:
            self._run_modules(ctx, modules)
            self.screen_log("")
            self.screen_log(f"Apply done. Summary: {ctx.summary_file}")
            self.screen_log(f"Report: {ctx.report_file}")
            self.screen_log(f"Log: {ctx.log_file}")
            self._set_summary_text(self._summary_from_ctx(ctx))
            if on_done == "full_apply":
                self.full_plan_file = None
                self.after(0, lambda: self.full_plan_label.configure(text="Full-run plan applied. No pending approval plan."))
            elif on_done == "manual_apply":
                self.manual_plan_file = None
                self.after(0, lambda: self.manual_plan_label.configure(text="Manual step plan applied. No pending approval plan."))
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled apply error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(text=f"Last apply: {ctx.run_id} | Report: {ctx.report_file}"))

    def _worker_undo_last_run(self, modules: list[str]):
        ctx = RunContext(CONFIG_PATH, dry_run=False, allow_renames=True, push=False, screen_log=self.screen_log)
        self._log_run_header(ctx, modules, "UNDO LAST APPLIED RUN")
        try:
            self._run_modules(ctx, modules)
            self.screen_log("")
            self.screen_log(f"Undo done. Summary: {ctx.summary_file}")
            self.screen_log(f"Report: {ctx.report_file}")
            self._set_summary_text(self._summary_from_ctx(ctx))
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled undo error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(text=f"Last undo: {ctx.run_id} | Report: {ctx.report_file}"))

    def _log_run_header(self, ctx: RunContext, modules: list[str], mode_label: str):
        self.screen_log("=" * 92)
        self.screen_log(f"Run ID: {ctx.run_id}")
        self.screen_log(f"Mode: {mode_label} | Include renames: {ctx.allow_renames} | Push: {ctx.push}")
        self.screen_log(f"Steps: {', '.join(LABEL_BY_MODULE.get(m, m) for m in modules)}")
        self.screen_log("=" * 92)

    def _run_modules(self, ctx: RunContext, modules: list[str]):
        for module_name in modules:
            label = LABEL_BY_MODULE.get(module_name, module_name)
            self.screen_log("")
            self.screen_log(f"--- {label} ---")
            module = importlib.import_module(f"steps.{module_name}")
            module.run(ctx)


if __name__ == "__main__":
    app = HousekeepingApp()
    app.mainloop()
