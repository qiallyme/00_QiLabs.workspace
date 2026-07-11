from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class QiPlugin:
    plugin_id = "system.creator_smoke_plugin"
    name = "Creator Smoke Plugin"
    category = "system"
    description = "Created by validation to confirm the New Tool flow."

    def build_view(self, host, parent):
        frame = tk.Frame(parent, bg=host.colors["panel"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=self.name, bg=host.colors["panel"], fg=host.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame, text=self.description, bg=host.colors["panel"], fg=host.colors["muted"], wraplength=760, justify="left").pack(anchor="w", pady=(6, 16))

        ttk.Button(frame, text="Run Sample Action", command=lambda: host.run_background(self.name, lambda: host.log("Hello from Creator Smoke Plugin."))).pack(anchor="w")

    def validate(self, host):
        host.log("Creator Smoke Plugin: validation OK")
