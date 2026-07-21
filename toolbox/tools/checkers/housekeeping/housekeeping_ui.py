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

# ── Phase 1 safe run (default) ────────────────────────────────────────────────
# QiSpark-only frontmatter pass. Indexes, full tree, git, renames, and link
# rewrites are intentionally excluded and must be run as manual advanced steps.
FULL_PREVIEW_STEPS = [
    "preflight",
    "validate_tags",
    "validate_templates",
    "scan_inventory",
    "normalize_frontmatter",
    "generate_report",
]

# Advanced full order (documented but NOT the default):
# preflight → validate_tags → validate_templates → scan_inventory →
# normalize_frontmatter → plan_filename_normalization → rewrite_links →
# rebuild_indexes → update_full_tree → update_git_manifest → generate_report

APPLY_STEPS_BASE = ["apply_saved_plan", "generate_report"]
UNDO_STEPS       = ["undo_last_run", "generate_report"]

MANUAL_STEPS = [
    ("preflight",                  "Preflight"),
    ("validate_tags",              "Validate tags"),
    ("validate_templates",         "Validate master template"),
    ("scan_inventory",             "Scan inventory"),
    ("normalize_frontmatter",      "Normalize frontmatter"),
    ("plan_filename_normalization","Plan filename normalization"),
    ("rewrite_links",              "Rewrite links from rename map"),
    ("rebuild_indexes",            "Rebuild folder indexes"),
    ("update_full_tree",           "Update QiLabs full tree"),
    ("update_git_manifest",        "Update Git manifest"),
    ("generate_report",            "Generate report"),
    ("git_commit_push",            "Recursive Git commit / push"),
    ("validate_qicode_frontmatter", "Validate QiCode frontmatter"),
    ("normalize_qicode_frontmatter", "Normalize QiCode frontmatter"),
    ("validate_qicode_codes",       "Validate QiCode codes"),
    ("rebuild_qicode_indexes",      "Rebuild QiCode indexes"),
    ("generate_qicode_audit_report","Generate QiCode audit report"),
]

LABEL_BY_MODULE = dict(MANUAL_STEPS) | {
    "apply_saved_plan": "Apply saved approval plan",
    "undo_last_run":    "Undo last applied run",
}

# Phase dropdown values and their backing module lists (preview-only for advanced)
PHASE_LABEL_P1       = "Phase 1 - QiSpark frontmatter only"
PHASE_LABEL_MANUAL   = "Manual - selected single step"
PHASE_LABEL_RENAMES  = "Advanced - rename preview only"
PHASE_LABEL_INDEXES  = "Advanced - indexes only"
PHASE_LABEL_TREE     = "Advanced - tree only"
PHASE_LABEL_GIT      = "Advanced - git manifest only"
PHASE_LABEL_QICODE   = "QiCode Maintenance - strict scope"

PHASE_OPTIONS = [
    PHASE_LABEL_P1,
    PHASE_LABEL_MANUAL,
    PHASE_LABEL_RENAMES,
    PHASE_LABEL_INDEXES,
    PHASE_LABEL_TREE,
    PHASE_LABEL_GIT,
    PHASE_LABEL_QICODE,
]

ADVANCED_PHASES = {
    PHASE_LABEL_RENAMES: ["plan_filename_normalization", "generate_report"],
    PHASE_LABEL_INDEXES: ["rebuild_indexes",             "generate_report"],
    PHASE_LABEL_TREE:    ["update_full_tree",            "generate_report"],
    PHASE_LABEL_GIT:     ["update_git_manifest",         "generate_report"],
    PHASE_LABEL_QICODE:  [
        "validate_qicode_frontmatter",
        "normalize_qicode_frontmatter",
        "validate_qicode_codes",
        "rebuild_qicode_indexes",
        "generate_qicode_audit_report"
    ],
}

SAFE_MANUAL_DEFAULT = "Normalize frontmatter"


class HousekeepingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QiLabs Housekeeping Console")
        self.geometry("1220x780")
        self.minsize(900, 560)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.current_thread: threading.Thread | None = None

        # Safety flags
        self.include_renames_var     = tk.BooleanVar(value=False)
        self.commit_after_apply_var  = tk.BooleanVar(value=False)
        self.push_after_commit_var   = tk.BooleanVar(value=False)

        # Plan state
        self.full_plan_file:   Path | None = None
        self.manual_plan_file: Path | None = None
        self.last_summary_file:Path | None = None

        # Dropdowns
        self.phase_var      = tk.StringVar(value=PHASE_LABEL_P1)
        self.manual_step_var= tk.StringVar(value=SAFE_MANUAL_DEFAULT)

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self._refresh_latest_manifest_summary()

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menubar()

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)

        # 1. Compact command bar — always visible, never scrolls
        self._build_command_bar(main)

        # 2. Plan-state label — always visible
        self.plan_state_label = ttk.Label(
            main,
            text="No plan loaded. Run Preview to begin.",
            foreground="#666",
            font=("Segoe UI", 9),
        )
        self.plan_state_label.pack(fill="x", padx=8, pady=(0, 2))

        # 3. Notebook — expands to fill all remaining space
        self._build_notebook(main)

        # 4. Status bar — always visible at bottom
        self.status = ttk.Label(
            main,
            text=f"Config: {CONFIG_PATH}",
            anchor="w",
            relief="sunken",
            font=("Segoe UI", 8),
        )
        self.status.pack(fill="x", side="bottom", ipady=2)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = tk.Menu(self)
        self.configure(menu=mb)

        # Run menu
        run_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Preview Selected Phase",          command=self.preview_selected_phase)
        run_menu.add_command(label="Approve / Apply Selected Phase",  command=self.approve_selected_phase)
        run_menu.add_separator()
        run_menu.add_command(label="Preview Phase 1 Safe Run",        command=self.preview_full_run)
        run_menu.add_command(label="Approve Saved Full Plan",         command=self.approve_full_plan)
        run_menu.add_separator()
        run_menu.add_command(label="Preview Selected Manual Step",    command=self.preview_manual_step)
        run_menu.add_command(label="Approve Selected Manual Step",    command=self.approve_manual_plan)
        run_menu.add_separator()
        run_menu.add_command(label="Undo Last Applied Run",           command=self.undo_last_applied_run)
        run_menu.add_separator()
        run_menu.add_command(label="Exit",                            command=self.destroy)

        # Open menu
        open_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Open", menu=open_menu)
        open_menu.add_command(label="Open Summary",            command=self.open_last_summary)
        open_menu.add_command(label="Open Summaries Folder",   command=lambda: self._open_path(ROOT / "summaries"))
        open_menu.add_command(label="Open Reports Folder",     command=lambda: self._open_path(ROOT / "reports"))
        open_menu.add_command(label="Open Plans Folder",       command=lambda: self._open_path(ROOT / "plans"))
        open_menu.add_command(label="Open Manifests Folder",   command=lambda: self._open_path(ROOT / "manifests"))
        open_menu.add_separator()
        open_menu.add_command(label="Open Housekeeping Folder",command=lambda: self._open_path(ROOT))

        # Safety menu
        safety_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Safety", menu=safety_menu)
        safety_menu.add_checkbutton(
            label="Include Filename Renames",
            variable=self.include_renames_var,
            onvalue=True, offvalue=False,
        )
        safety_menu.add_checkbutton(
            label="Commit After Apply",
            variable=self.commit_after_apply_var,
            onvalue=True, offvalue=False,
        )
        safety_menu.add_checkbutton(
            label="Push After Commit",
            variable=self.push_after_commit_var,
            onvalue=True, offvalue=False,
        )
        safety_menu.add_separator()
        safety_menu.add_command(label="Reset Safe Defaults", command=self.reset_safe_defaults)

    # ── Compact command bar ───────────────────────────────────────────────────

    def _build_command_bar(self, parent):
        bar = ttk.Frame(parent, padding=(6, 6, 6, 4))
        bar.pack(fill="x")

        # Phase dropdown
        ttk.Label(bar, text="Phase:").pack(side="left")
        self.phase_combo = ttk.Combobox(
            bar,
            textvariable=self.phase_var,
            values=PHASE_OPTIONS,
            state="readonly",
            width=32,
        )
        self.phase_combo.pack(side="left", padx=(4, 12))

        # Manual step dropdown (only active when Manual phase selected)
        ttk.Label(bar, text="Step:").pack(side="left")
        self.manual_combo = ttk.Combobox(
            bar,
            textvariable=self.manual_step_var,
            values=[label for _, label in MANUAL_STEPS],
            state="readonly",
            width=28,
        )
        self.manual_combo.pack(side="left", padx=(4, 12))

        sep = ttk.Separator(bar, orient="vertical")
        sep.pack(side="left", fill="y", padx=6)

        ttk.Button(bar, text="Preview",  width=10, command=self.preview_selected_phase).pack(side="left", padx=2)
        ttk.Button(bar, text="Approve",  width=10, command=self.approve_selected_phase).pack(side="left", padx=2)
        ttk.Button(bar, text="Undo",     width=8,  command=self.undo_last_applied_run).pack(side="left", padx=2)
        ttk.Button(bar, text="Cancel",   width=8,  command=self._cancel_current_plan).pack(side="left", padx=2)

        sep2 = ttk.Separator(bar, orient="vertical")
        sep2.pack(side="left", fill="y", padx=6)

        ttk.Button(bar, text="Clear Log", width=10, command=self.clear_log).pack(side="left", padx=2)
        ttk.Button(bar, text="Refresh",   width=9,  command=self._refresh_latest_manifest_summary).pack(side="left", padx=2)

    # ── Notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        # ── Tab 1: Summary ────────────────────────────────────────────────────
        summary_tab = ttk.Frame(nb, padding=6)
        nb.add(summary_tab, text="Summary")

        self.summary_text = tk.Text(
            summary_tab, wrap="word", font=("Consolas", 10), state="normal"
        )
        sum_scroll = ttk.Scrollbar(summary_tab, orient="vertical", command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=sum_scroll.set)
        sum_scroll.pack(side="right", fill="y")
        self.summary_text.pack(side="left", fill="both", expand=True)

        # ── Tab 2: Output Log ─────────────────────────────────────────────────
        log_tab = ttk.Frame(nb, padding=6)
        nb.add(log_tab, text="Output Log")

        self.output = tk.Text(
            log_tab, wrap="word", font=("Consolas", 10), state="normal"
        )
        log_scroll = ttk.Scrollbar(log_tab, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.output.pack(side="left", fill="both", expand=True)

        # ── Tab 3: Safety / Current Plan ──────────────────────────────────────
        plan_tab = ttk.Frame(nb, padding=8)
        nb.add(plan_tab, text="Safety / Plan")

        # Safety flags
        flags_frame = ttk.LabelFrame(plan_tab, text="Safety Flags", padding=8)
        flags_frame.pack(fill="x", pady=(0, 8))

        ttk.Checkbutton(
            flags_frame,
            text="Include filename renames in plan",
            variable=self.include_renames_var,
        ).grid(row=0, column=0, sticky="w", padx=8, pady=2)
        ttk.Checkbutton(
            flags_frame,
            text="Commit after apply",
            variable=self.commit_after_apply_var,
        ).grid(row=0, column=1, sticky="w", padx=8, pady=2)
        ttk.Checkbutton(
            flags_frame,
            text="Push after commit",
            variable=self.push_after_commit_var,
        ).grid(row=0, column=2, sticky="w", padx=8, pady=2)
        ttk.Button(
            flags_frame,
            text="Reset Safe Defaults",
            command=self.reset_safe_defaults,
        ).grid(row=0, column=3, sticky="e", padx=8, pady=2)
        flags_frame.columnconfigure(3, weight=1)

        # Current plan info
        plan_info_frame = ttk.LabelFrame(plan_tab, text="Current Plan Files", padding=8)
        plan_info_frame.pack(fill="both", expand=True)

        self.plan_info_text = tk.Text(
            plan_info_frame, wrap="word", font=("Consolas", 9), height=12
        )
        plan_info_scroll = ttk.Scrollbar(plan_info_frame, orient="vertical", command=self.plan_info_text.yview)
        self.plan_info_text.configure(yscrollcommand=plan_info_scroll.set)
        plan_info_scroll.pack(side="right", fill="y")
        self.plan_info_text.pack(side="left", fill="both", expand=True)

        self._update_plan_info()

    # ─── Phase logic ──────────────────────────────────────────────────────────

    def preview_selected_phase(self):
        phase = self.phase_var.get()
        if phase == PHASE_LABEL_P1:
            self.preview_full_run()
        elif phase == PHASE_LABEL_MANUAL:
            self.preview_manual_step()
        elif phase in ADVANCED_PHASES:
            if self._busy():
                return
            modules = ADVANCED_PHASES[phase]
            self._set_plan_state(f"Building advanced preview: {phase} ...")
            self._start_worker(
                target=self._worker_preview,
                modules=modules,
                plan_kind="advanced",
                allow_renames=self.include_renames_var.get(),
                on_done=f"adv_{phase}",
            )
        else:
            messagebox.showwarning("Unknown phase", f"Unrecognised phase: {phase}")

    def approve_selected_phase(self):
        phase = self.phase_var.get()
        if phase == PHASE_LABEL_P1:
            self.approve_full_plan()
        elif phase == PHASE_LABEL_MANUAL:
            self.approve_manual_plan()
        elif phase in ADVANCED_PHASES:
            messagebox.showwarning(
                "Advanced phase — preview only",
                "Advanced phases are preview-only from this screen.\n\n"
                "Switch to 'Manual - selected single step' and choose the specific step "
                "if you want to intentionally apply it.",
            )
        else:
            messagebox.showwarning("Unknown phase", f"Unrecognised phase: {phase}")

    # ─── Reset ────────────────────────────────────────────────────────────────

    def reset_safe_defaults(self):
        self.include_renames_var.set(False)
        self.commit_after_apply_var.set(False)
        self.push_after_commit_var.set(False)
        self.phase_var.set(PHASE_LABEL_P1)
        self.manual_step_var.set(SAFE_MANUAL_DEFAULT)
        self._set_plan_state("Safe defaults restored.")
        self.screen_log("[INFO] Safe defaults restored.")

    # ─── Full run (Phase 1) ───────────────────────────────────────────────────

    def preview_full_run(self):
        if self._busy():
            return
        self.full_plan_file = None
        self._set_plan_state("Building Phase 1 preview plan...")
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
            messagebox.showwarning("No full-run plan", "Run Preview first, then approve.")
            return
        msg = (
            f"Apply the saved full-run plan?\n\n{self.full_plan_file}\n\n"
            "This does not rescan. It applies the exact file actions from the preview."
        )
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

    def cancel_full_plan(self):
        self.full_plan_file = None
        self._set_plan_state("Full-run preview canceled. No saved plan loaded.")
        self.screen_log("[INFO] Full-run preview plan canceled in UI. No files changed.")

    # ─── Manual step ──────────────────────────────────────────────────────────

    def preview_manual_step(self):
        if self._busy():
            return
        module = self._selected_manual_module()
        self.manual_plan_file = None
        self._set_plan_state(f"Building manual preview: {LABEL_BY_MODULE.get(module, module)} ...")
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
            messagebox.showwarning("No manual plan", "Run Preview Step first, then approve.")
            return
        msg = (
            f"Apply this saved manual step plan?\n\n{self.manual_plan_file}\n\n"
            "This applies the exact file actions from that step preview."
        )
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
        self._set_plan_state("Manual step preview canceled. No saved plan loaded.")
        self.screen_log("[INFO] Manual preview plan canceled in UI. No files changed.")

    def _cancel_current_plan(self):
        """Cancel whichever plan is currently loaded."""
        if self.full_plan_file:
            self.cancel_full_plan()
        elif self.manual_plan_file:
            self.cancel_manual_plan()
        else:
            self._set_plan_state("No plan to cancel.")

    # ─── Undo ─────────────────────────────────────────────────────────────────

    def undo_last_applied_run(self):
        if self._busy():
            return
        pointer = ROOT / "manifests" / "latest_apply_manifest.json"
        if not pointer.exists():
            messagebox.showinfo("No manifest", "There is no applied run manifest to undo yet.")
            return
        if not messagebox.askyesno(
            "Undo last applied run",
            "Undo the last applied housekeeping run?\n\n"
            "Changed/moved files are skipped safely and logged. "
            "Git commits/pushes are not auto-reversed.",
        ):
            return
        self._start_worker(target=self._worker_undo_last_run, modules=UNDO_STEPS)

    # ─── Open helpers ─────────────────────────────────────────────────────────

    def _open_path(self, path: Path | str | None):
        if not path:
            messagebox.showinfo("Nothing to open", "No file/folder is available yet.")
            return
        p = Path(path)
        if not p.exists():
            messagebox.showwarning("Missing", f"Path does not exist:\n{p}")
            return
        try:
            os.startfile(str(p))
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))

    def open_last_summary(self):
        self._open_path(self.last_summary_file)

    # ─── Summary text helpers ─────────────────────────────────────────────────

    def _set_summary_text(self, text: str):
        def update():
            self.summary_text.delete("1.0", "end")
            self.summary_text.insert("end", text)
        self.after(0, update)

    def _set_plan_state(self, text: str):
        def update():
            self.plan_state_label.configure(text=text)
            self._update_plan_info()
        self.after(0, update)

    def _update_plan_info(self):
        lines = []
        if self.full_plan_file:
            lines.append(f"Full-run plan:   {self.full_plan_file}")
        else:
            lines.append("Full-run plan:   (none)")
        if self.manual_plan_file:
            lines.append(f"Manual step plan:{self.manual_plan_file}")
        else:
            lines.append("Manual step plan:(none)")
        lines.append("")
        lines.append(f"Safety flags:")
        lines.append(f"  Include renames : {self.include_renames_var.get()}")
        lines.append(f"  Commit on apply : {self.commit_after_apply_var.get()}")
        lines.append(f"  Push on commit  : {self.push_after_commit_var.get()}")
        lines.append("")
        lines.append(f"Config: {CONFIG_PATH}")
        try:
            self.plan_info_text.delete("1.0", "end")
            self.plan_info_text.insert("end", "\n".join(lines))
        except AttributeError:
            pass  # widget not yet built

    def _summary_from_plan(self, plan_file: Path) -> str:
        try:
            data     = json.loads(Path(plan_file).read_text(encoding="utf-8"))
            actions  = data.get("actions", [])
            warnings = data.get("warnings", [])
            errors   = data.get("errors", [])
            writes   = sum(1 for a in actions if a.get("type") == "write_text")
            renames  = sum(1 for a in actions if a.get("type") == "rename")
            status   = "Needs review" if errors else ("Completed with warnings" if warnings else "Ready to approve")
            report   = data.get("report_file", "")
            self.last_summary_file = Path(report) if report else None
            lines = [
                f"Status:          {status}",
                f"Preview run:     {data.get('run_id')}",
                f"Plan kind:       {data.get('plan_kind')}",
                f"Actions planned: {len(actions)}  | Writes: {writes}  | Renames: {renames}",
                f"Warnings:        {len(warnings)}  | Errors: {len(errors)}",
                f"Plan:            {plan_file}",
                f"Report:          {report}",
            ]
            if warnings:
                lines.append("Top warning: " + str(warnings[0])[:220])
            if errors:
                lines.append("Top error: "   + str(errors[0])[:220])
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not summarize plan: {exc}\nPlan: {plan_file}"

    def _summary_from_ctx(self, ctx: RunContext) -> str:
        s = ctx.state.get("run_summary", {})
        if not s:
            return f"Run complete: {ctx.run_id}\nReport: {ctx.report_file}"
        self.last_summary_file = Path(s.get("summary_file") or ctx.summary_file)
        lines = [
            f"Status:   {s.get('status')}",
            f"Run:      {s.get('run_id')}  | Mode: {s.get('mode')}",
            f"Planned:  {s.get('planned_actions')}  | Writes: {s.get('planned_writes')}  | Renames: {s.get('planned_renames')}",
            f"Applied:  {s.get('applied_actions')}  | Skipped: {s.get('skipped_actions')}  | Changed: {s.get('changed_files')}",
            f"Warnings: {s.get('warnings')}  | Errors: {s.get('errors')}",
            f"Summary:  {s.get('summary_file')}",
            f"Report:   {s.get('report_file')}",
        ]
        if s.get("apply_manifest_file"):
            lines.append(f"Undo source manifest: {s.get('apply_manifest_file')}")
        if s.get("undo_manifest_file"):
            lines.append(f"Undo manifest: {s.get('undo_manifest_file')}")
        return "\n".join(lines)

    def _refresh_latest_manifest_summary(self):
        pointer = ROOT / "manifests" / "latest_apply_manifest.json"
        if not pointer.exists():
            self._set_summary_text(
                "No applied run manifest yet.\nFirst run will create one after Approve + Apply."
            )
            return
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            self._set_summary_text(
                "Latest applied run manifest\n"
                f"Run:      {data.get('apply_run_id')}\n"
                f"Created:  {data.get('created_at')}\n"
                f"Manifest: {data.get('latest_apply_manifest')}\n"
                f"Summary:\n{json.dumps(data.get('summary', {}), indent=2)}"
            )
        except Exception as exc:
            self._set_summary_text(f"Could not read latest manifest pointer: {exc}")

    # ─── Log ─────────────────────────────────────────────────────────────────

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

    # ─── Worker infrastructure ────────────────────────────────────────────────

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

    def _start_worker(self, target, **kwargs):
        self.after(0, lambda: self.status.configure(text="Running..."))
        self.current_thread = threading.Thread(target=target, kwargs=kwargs, daemon=True)
        self.current_thread.start()

    # ─── Worker methods ───────────────────────────────────────────────────────

    def _worker_preview(self, modules: list[str], plan_kind: str, allow_renames: bool, on_done: str):
        ctx = RunContext(CONFIG_PATH, dry_run=True, allow_renames=allow_renames, push=False, screen_log=self.screen_log)
        self._log_run_header(ctx, modules, "PREVIEW")
        try:
            self._run_modules(ctx, modules)
            plan_file = ctx.save_plan(modules=modules, plan_kind=plan_kind)
            self.screen_log("")
            self.screen_log(f"Preview done. Approval plan: {plan_file}")
            self.screen_log(f"Summary: {ctx.summary_file}")
            self.screen_log(f"Report:  {ctx.report_file}")
            self._set_summary_text(self._summary_from_plan(plan_file))
            if on_done == "full_preview":
                self.full_plan_file = plan_file
                self._set_plan_state(f"Phase 1 plan ready to approve: {plan_file.name}")
            elif on_done == "manual_preview":
                self.manual_plan_file = plan_file
                self._set_plan_state(f"Manual plan ready to approve: {plan_file.name}")
            else:
                # advanced phases — preview only, no approve path
                self._set_plan_state(f"Advanced preview done (read-only): {plan_file.name}")
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled preview error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(
                text=f"Last preview: {ctx.run_id} | Plan: {ctx.plan_file}"
            ))

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
            self.screen_log(f"Log:    {ctx.log_file}")
            self._set_summary_text(self._summary_from_ctx(ctx))
            if on_done == "full_apply":
                self.full_plan_file = None
                self._set_plan_state("Phase 1 plan applied. No pending plan.")
            elif on_done == "manual_apply":
                self.manual_plan_file = None
                self._set_plan_state("Manual step plan applied. No pending plan.")
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled apply error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(
                text=f"Last apply: {ctx.run_id} | Report: {ctx.report_file}"
            ))

    def _worker_undo_last_run(self, modules: list[str]):
        ctx = RunContext(CONFIG_PATH, dry_run=False, allow_renames=True, push=False, screen_log=self.screen_log)
        self._log_run_header(ctx, modules, "UNDO LAST APPLIED RUN")
        try:
            self._run_modules(ctx, modules)
            self.screen_log("")
            self.screen_log(f"Undo done. Summary: {ctx.summary_file}")
            self.screen_log(f"Report: {ctx.report_file}")
            self._set_summary_text(self._summary_from_ctx(ctx))
            self._set_plan_state("Undo complete.")
        except Exception as exc:
            tb = traceback.format_exc()
            ctx.error(f"Unhandled undo error: {exc}")
            self.screen_log(tb)
        finally:
            self.after(0, lambda: self.status.configure(
                text=f"Last undo: {ctx.run_id} | Report: {ctx.report_file}"
            ))

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
