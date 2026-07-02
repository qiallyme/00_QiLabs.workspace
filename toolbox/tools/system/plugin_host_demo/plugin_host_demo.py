from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk


class QiPlugin:
    plugin_id = "system.plugin_host_demo"
    name = "Plugin Host Demo"
    category = "system"
    description = "Demonstrates the native QiPlugin v2 host API."

    def build_view(self, host, parent):
        frame = tk.Frame(parent, bg=host.colors["panel"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=self.name, bg=host.colors["panel"], fg=host.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame, text=self.description, bg=host.colors["panel"], fg=host.colors["muted"], wraplength=760, justify="left").pack(anchor="w", pady=(6, 16))

        workspace = tk.StringVar(value=host.get_workspace())
        row = tk.Frame(frame, bg=host.colors["panel"])
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="Workspace", bg=host.colors["panel"], fg=host.colors["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Entry(row, textvariable=workspace, bg=host.colors["panel_2"], fg=host.colors["text"], insertbackground=host.colors["text"], relief="flat").pack(fill="x", ipady=8, pady=(4, 0))

        buttons = tk.Frame(frame, bg=host.colors["panel"])
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Log Workspace", command=lambda: host.log(f"Workspace: {workspace.get()}")).pack(side="left")
        ttk.Button(buttons, text="Use Workspace", command=lambda: host.set_workspace(workspace.get())).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Run Background Demo", command=lambda: self.run_demo(host)).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Validate Me", command=lambda: self.validate(host)).pack(side="left", padx=(8, 0))

    def run_demo(self, host):
        def work():
            for index in range(1, 4):
                host.log(f"Background step {index}/3")
                time.sleep(0.4)

        host.run_background("Plugin Host Demo", work, on_done=lambda _result: host.set_status("Demo complete"))

    def validate(self, host):
        host.log("Plugin Host Demo validation OK.")
