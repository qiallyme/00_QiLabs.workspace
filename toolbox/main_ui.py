from __future__ import annotations

import queue
import sys
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from toolbox_core.plugin_autofix import autofix_all
from toolbox_core.plugin_creator import create_plugin as scaffold_plugin
from toolbox_core.plugin_host import PluginHost
from toolbox_core.plugin_loader import load_plugins
from toolbox_core.plugin_registry import load_registry, save_registry


COLORS = {
    "bg": "#090d13",
    "bg_2": "#0d131b",
    "sidebar": "#0f1722",
    "sidebar_2": "#121d2a",
    "panel": "#151f2b",
    "panel_2": "#1b2937",
    "panel_3": "#26384a",
    "panel_soft": "#101923",
    "border": "#2f455a",
    "border_soft": "#223244",
    "text": "#f4f7fb",
    "muted": "#9aabba",
    "muted_2": "#6f8294",
    "accent": "#65dbc8",
    "accent_2": "#98f0e5",
    "accent_dark": "#143b43",
    "success": "#72e08f",
    "danger": "#ff6b7a",
    "warning": "#ffd166",
    "console_bg": "#061019",
    "console_text": "#dcffe8",
}


class CreatePluginDialog(tk.Toplevel):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.title("Create Plugin")
        self.geometry("700x560")
        self.configure(bg=COLORS["bg"])
        self.result = None

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar(value="custom")
        self.description_var = tk.StringVar()
        self.type_var = tk.StringVar(value="native")

        body = tk.Frame(self, bg=COLORS["panel"], padx=14, pady=14, highlightthickness=1, highlightbackground=COLORS["border_soft"])
        body.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(body, text="Create Plugin", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(body, text="Scaffold a valid plugin folder under tools/<category>/<name>.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))
        self._field(body, "Plugin name", self.name_var)
        self._field(body, "Category", self.category_var)
        self._field(body, "Description", self.description_var)

        tk.Label(body, text="Plugin type", bg=COLORS["panel"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 3))
        type_row = tk.Frame(body, bg=COLORS["panel"])
        type_row.pack(fill="x")
        for label, value in (("Native", "native"), ("Legacy BaseTool", "legacy"), ("Script", "script")):
            ttk.Radiobutton(type_row, text=label, value=value, variable=self.type_var).pack(side="left", padx=(0, 12))

        tk.Label(body, text="Optional Python body", bg=COLORS["panel"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(10, 3))
        self.body_text = tk.Text(body, height=10, bg=COLORS["console_bg"], fg=COLORS["console_text"], insertbackground=COLORS["console_text"], relief="flat", wrap="none", padx=8, pady=8)
        self.body_text.pack(fill="both", expand=True)
        self.body_text.insert("1.0", 'print("Hello from my new QiLabs plugin.")')

        buttons = tk.Frame(body, bg=COLORS["panel"])
        buttons.pack(fill="x", pady=(10, 0))
        self._button(buttons, "Create", self.ok, COLORS["accent"], "#061014").pack(side="left")
        self._button(buttons, "Cancel", self.destroy, COLORS["panel_3"], COLORS["text"]).pack(side="left", padx=(8, 0))

        self.transient(master)
        self.grab_set()
        self.wait_window(self)

    def _button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", bd=0, padx=12, pady=7, cursor="hand2", font=("Segoe UI", 9, "bold"))

    def _field(self, parent: tk.Widget, label: str, var: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 3))
        tk.Entry(parent, textvariable=var, bg=COLORS["panel_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat").pack(fill="x", ipady=7)

    def ok(self) -> None:
        self.result = {
            "name": self.name_var.get().strip(),
            "category": self.category_var.get().strip(),
            "description": self.description_var.get().strip(),
            "plugin_type": self.type_var.get(),
            "script_body": self.body_text.get("1.0", "end").strip(),
        }
        self.destroy()


class QiLabsToolbox(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QiLabs Toolbox")
        self.geometry("1380x840")
        self.minsize(980, 640)
        self.configure(bg=COLORS["bg"])
        self.colors = COLORS
        self.ui_queue: "queue.Queue[callable]" = queue.Queue()
        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.active_name_var = tk.StringVar(value="Select a plugin")
        self.active_meta_var = tk.StringVar(value="Refresh plugins if the list is empty.")
        self.validation_var = tk.StringVar(value="Validation not run")
        self.adapters = []
        self.active_adapter = None
        self.card_by_id: dict[str, tk.Frame] = {}
        self.console_visible = True

        self.host = PluginHost(
            ROOT,
            workspace_getter=lambda: self.workspace_var.get(),
            workspace_setter=lambda value: self.workspace_var.set(value),
            log_callback=self.log,
            status_callback=lambda value: self.status_var.set(value),
            refresh_callback=self.refresh_plugins,
            ui_dispatch=self.dispatch,
            colors=self.colors,
        )

        self.setup_styles()
        self.build_layout()
        self.search_var.trace_add("write", lambda *_: self.populate_sidebar())
        self.after(50, self.process_queue)
        self.refresh_plugins()

    def setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=(9, 6), borderwidth=0, font=("Segoe UI", 9))
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TRadiobutton", background=COLORS["panel"], foreground=COLORS["text"])
        style.configure("Vertical.TScrollbar", background=COLORS["panel_2"], troughcolor=COLORS["sidebar"], bordercolor=COLORS["sidebar"], arrowcolor=COLORS["muted"])
        style.map("TButton", background=[("active", COLORS["accent_2"])])

    def button(self, parent, text, command, bg=None, fg=None, bold=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg or COLORS["panel_3"],
            fg=fg or COLORS["text"],
            activebackground=bg or COLORS["panel_3"],
            activeforeground=fg or COLORS["text"],
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            font=("Segoe UI", 9, "bold" if bold else "normal"),
        )

    def build_layout(self) -> None:
        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(outer, bg=COLORS["sidebar"], width=305)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        main = tk.Frame(outer, bg=COLORS["bg"])
        main.pack(side="left", fill="both", expand=True)

        self.build_sidebar()
        self.build_header(main)
        self.build_workspace(main)

        self.content = tk.PanedWindow(main, orient="vertical", bg=COLORS["bg"], sashwidth=5, bd=0, showhandle=False)
        self.content.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.plugin_container = tk.Frame(self.content, bg=COLORS["panel"], padx=10, pady=10, highlightthickness=1, highlightbackground=COLORS["border_soft"])
        self.console_panel = tk.Frame(self.content, bg=COLORS["panel_soft"], padx=8, pady=8, highlightthickness=1, highlightbackground=COLORS["border_soft"])
        self.content.add(self.plugin_container, minsize=330)
        self.content.add(self.console_panel, minsize=145)
        self.build_console()
        self.build_footer(main)

    def build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=14, pady=12)
        brand.pack(fill="x")
        tk.Label(brand, text="QiLabs", bg=COLORS["sidebar"], fg=COLORS["text"], font=("Segoe UI Semibold", 19)).pack(anchor="w")
        tk.Label(brand, text="Toolbox plugin host", bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(1, 0))

        search = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=12, pady=4)
        search.pack(fill="x")
        tk.Entry(search, textvariable=self.search_var, bg=COLORS["sidebar_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat").pack(fill="x", ipady=8)

        controls = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=12, pady=8)
        controls.pack(fill="x")
        self.button(controls, "Refresh", self.refresh_plugins).pack(side="left")
        self.button(controls, "Validate", lambda: self.host.validate_plugin()).pack(side="left", padx=(6, 0))
        self.button(controls, "Fix", self.autofix).pack(side="left", padx=(6, 0))
        self.button(controls, "+", self.create_plugin, bg=COLORS["accent"], fg="#061014", bold=True).pack(side="left", padx=(6, 0))

        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=COLORS["sidebar"], highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.sidebar_canvas.yview)
        self.plugin_list = tk.Frame(self.sidebar_canvas, bg=COLORS["sidebar"])
        self.plugin_list.bind("<Configure>", lambda _e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.create_window((0, 0), window=self.plugin_list, anchor="nw", width=287)
        self.sidebar_canvas.configure(yscrollcommand=scroll.set)
        self.sidebar_canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        scroll.pack(side="right", fill="y", pady=(0, 8))

    def build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=COLORS["bg"], padx=12, pady=10)
        header.pack(fill="x")
        left = tk.Frame(header, bg=COLORS["bg"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, textvariable=self.active_name_var, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(left, textvariable=self.active_meta_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        right = tk.Frame(header, bg=COLORS["bg"])
        right.pack(side="right")
        tk.Label(right, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["accent_2"], font=("Segoe UI", 9, "bold")).pack(anchor="e")
        tk.Label(right, textvariable=self.validation_var, bg=COLORS["bg"], fg=COLORS["muted_2"], font=("Segoe UI", 8)).pack(anchor="e", pady=(2, 0))

    def build_workspace(self, parent: tk.Widget) -> None:
        wrap = tk.Frame(parent, bg=COLORS["panel_soft"], padx=10, pady=8, highlightthickness=1, highlightbackground=COLORS["border_soft"])
        wrap.pack(fill="x", padx=10, pady=(0, 8))
        row = tk.Frame(wrap, bg=COLORS["panel_soft"])
        row.pack(fill="x")
        tk.Label(row, text="Workspace", bg=COLORS["panel_soft"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold"), width=10, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.workspace_var, bg=COLORS["panel_2"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat").pack(side="left", fill="x", expand=True, ipady=7)
        self.button(row, "Browse", self.browse_workspace).pack(side="left", padx=(6, 0))
        self.button(row, "Open", lambda: self.host.open_folder(self.workspace_var.get())).pack(side="left", padx=(6, 0))
        self.button(row, "Console", self.toggle_console).pack(side="left", padx=(6, 0))

    def build_console(self) -> None:
        top = tk.Frame(self.console_panel, bg=COLORS["panel_soft"])
        top.pack(fill="x", pady=(0, 5))
        tk.Label(top, text="Output", bg=COLORS["panel_soft"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.button(top, "Clear", lambda: self.console.delete("1.0", "end")).pack(side="right")
        self.console = tk.Text(self.console_panel, height=8, bg=COLORS["console_bg"], fg=COLORS["console_text"], insertbackground=COLORS["console_text"], relief="flat", wrap="word", padx=8, pady=8, font=("Cascadia Code", 9))
        self.console.pack(fill="both", expand=True)

    def build_footer(self, parent: tk.Widget) -> None:
        footer = tk.Frame(parent, bg=COLORS["bg"], padx=12, pady=0)
        footer.pack(fill="x", pady=(0, 8))
        self.footer_var = tk.StringVar(value=f"Root: {ROOT}")
        tk.Label(footer, textvariable=self.footer_var, bg=COLORS["bg"], fg=COLORS["muted_2"], font=("Segoe UI", 8)).pack(anchor="w")

    def toggle_console(self) -> None:
        if self.console_visible:
            self.content.forget(self.console_panel)
            self.console_visible = False
        else:
            self.content.add(self.console_panel, minsize=145)
            self.console_visible = True

    def dispatch(self, callback) -> None:
        self.ui_queue.put(callback)

    def process_queue(self) -> None:
        while True:
            try:
                callback = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                self.log("UI DISPATCH ERROR:\n" + traceback.format_exc())
        self.after(50, self.process_queue)

    def log(self, message: str) -> None:
        self.console.insert("end", str(message).rstrip() + "\n")
        self.console.see("end")

    def browse_workspace(self) -> None:
        path = filedialog.askdirectory(initialdir=self.workspace_var.get() or str(ROOT))
        if path:
            self.workspace_var.set(path)

    def refresh_plugins(self) -> None:
        try:
            save_registry(ROOT)
            self.adapters = load_plugins(ROOT)
            registry = load_registry(ROOT)
            self.validation_var.set(f"{registry.get('errors', 0)} errors / {registry.get('warnings', 0)} warnings / {len(self.adapters)} loaded")
            self.populate_sidebar()
            self.log(f"Refreshed plugins: {len(self.adapters)} loaded")
            if self.adapters and self.active_adapter is None:
                self.select_plugin(self.adapters[0])
        except Exception:
            messagebox.showerror("Refresh failed", traceback.format_exc())
            self.log("REFRESH FAILED:\n" + traceback.format_exc())

    def populate_sidebar(self) -> None:
        for child in self.plugin_list.winfo_children():
            child.destroy()
        self.card_by_id.clear()
        query = self.search_var.get().strip().lower()
        adapters = [a for a in self.adapters if query in f"{a.name} {a.category} {a.plugin_id} {a.description}".lower()]
        current_category = None
        for adapter in adapters:
            if adapter.category != current_category:
                current_category = adapter.category
                tk.Label(self.plugin_list, text=current_category.upper(), bg=COLORS["sidebar"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(9, 4))
            self._plugin_card(adapter)
        if not adapters:
            tk.Label(self.plugin_list, text="No plugins found.", bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=16)

    def _plugin_card(self, adapter) -> None:
        active = self.active_adapter is adapter
        bg = COLORS["accent_dark"] if active else COLORS["sidebar_2"]
        border = COLORS["accent"] if active else COLORS["border_soft"]
        card = tk.Frame(self.plugin_list, bg=bg, padx=9, pady=7, highlightthickness=1, highlightbackground=border, cursor="hand2")
        card.pack(fill="x", padx=7, pady=(0, 6))
        title = tk.Label(card, text=adapter.name, bg=bg, fg=COLORS["text"], font=("Segoe UI", 9, "bold"), anchor="w")
        title.pack(fill="x")
        meta = tk.Label(card, text=adapter.plugin_id, bg=bg, fg=COLORS["muted"], font=("Segoe UI", 7), anchor="w")
        meta.pack(fill="x", pady=(2, 0))
        for widget in (card, title, meta):
            widget.bind("<Button-1>", lambda _e, item=adapter: self.select_plugin(item))
        self.card_by_id[adapter.plugin_id] = card

    def select_plugin(self, adapter) -> None:
        if self.active_adapter is not None:
            try:
                self.active_adapter.deactivate(self.host)
            except Exception:
                self.log("DEACTIVATE ERROR:\n" + traceback.format_exc())
        self.active_adapter = adapter
        for child in self.plugin_container.winfo_children():
            child.destroy()
        self.populate_sidebar()
        self.active_name_var.set(adapter.name)
        self.active_meta_var.set(f"{adapter.category} / {adapter.plugin_id}")
        self.footer_var.set(f"Workspace: {self.workspace_var.get()}    Selected: {adapter.plugin_id}    Root: {ROOT}")
        self.log(f"OPEN: {adapter.plugin_id} [{adapter.__class__.__name__}]")
        try:
            adapter.activate(self.host)
            adapter.build_view(self.host, self.plugin_container)
            self.status_var.set(f"Loaded {adapter.name}")
        except Exception:
            tb = traceback.format_exc()
            self.log("PLUGIN VIEW ERROR:\n" + tb)
            self.status_var.set(f"Plugin failed: {adapter.name}")
            tk.Label(self.plugin_container, text=f"Plugin failed to open: {adapter.name}", bg=COLORS["panel"], fg=COLORS["danger"], font=("Segoe UI", 15, "bold")).pack(anchor="w")
            tk.Label(self.plugin_container, text=str(adapter.manifest_path), bg=COLORS["panel"], fg=COLORS["muted"], wraplength=850, justify="left").pack(anchor="w", pady=(4, 8))
            err = tk.Text(self.plugin_container, bg=COLORS["console_bg"], fg=COLORS["console_text"], relief="flat", wrap="word", padx=8, pady=8)
            err.pack(fill="both", expand=True)
            err.insert("1.0", tb)
            err.configure(state="disabled")

    def autofix(self) -> None:
        preview = autofix_all(ROOT, apply=False)
        count = len(preview.get("actions", []))
        if count == 0:
            self.log("Auto-Fix preview found no actions.")
            return
        if not messagebox.askyesno("Auto-Fix", f"Preview found {count} safe actions. Apply them now?"):
            return
        result = autofix_all(ROOT, apply=True)
        self.log(f"Auto-Fix applied {len(result.get('actions', []))} actions.")
        self.refresh_plugins()

    def create_plugin(self) -> None:
        dialog = CreatePluginDialog(self)
        if not dialog.result:
            return
        data = dialog.result
        if not data["name"]:
            messagebox.showerror("Missing name", "Plugin name is required.")
            return
        try:
            plugin_dir = scaffold_plugin(ROOT, **data)
            self.log(f"Created plugin: {plugin_dir}")
            self.refresh_plugins()
            for adapter in self.adapters:
                if Path(adapter.plugin_dir) == plugin_dir:
                    self.select_plugin(adapter)
                    break
        except Exception:
            messagebox.showerror("Create plugin failed", traceback.format_exc())
            self.log("CREATE FAILED:\n" + traceback.format_exc())



# --- QILABS V0.6 SIDEBAR SCROLL PATCH ---
def _qilabs_v06_is_descendant(widget, ancestor):
    try:
        while widget is not None:
            if widget == ancestor:
                return True
            widget = getattr(widget, "master", None)
    except Exception:
        return False
    return False


def _qilabs_v06_enable_sidebar_scroll(self):
    """Force reliable mousewheel + resize behavior for the toolbox sidebar."""
    canvas = getattr(self, "sidebar_canvas", None)
    inner = getattr(self, "sidebar_inner", None)
    sidebar = getattr(self, "sidebar", None)
    if canvas is None or inner is None or sidebar is None:
        return

    def sync_scrollregion(_event=None):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def sync_width(event=None):
        try:
            width = max(220, canvas.winfo_width() - 6)
            for item in canvas.find_all():
                if canvas.type(item) == "window":
                    canvas.itemconfigure(item, width=width)
        except Exception:
            pass
        sync_scrollregion()

    def wheel(event):
        try:
            target = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        except Exception:
            target = None
        if not _qilabs_v06_is_descendant(target, sidebar):
            return None
        try:
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(3, "units")
            else:
                delta = int(getattr(event, "delta", 0))
                if delta == 0:
                    return "break"
                canvas.yview_scroll(-1 * int(delta / 120) * 3, "units")
            sync_scrollregion()
            return "break"
        except Exception:
            return None

    # Bind globally but only act when the pointer is inside the sidebar.
    try:
        self.bind_all("<MouseWheel>", wheel, add="+")
        self.bind_all("<Button-4>", wheel, add="+")
        self.bind_all("<Button-5>", wheel, add="+")
    except Exception:
        pass

    try:
        inner.bind("<Configure>", sync_scrollregion, add="+")
        canvas.bind("<Configure>", sync_width, add="+")
        canvas.after_idle(sync_width)
        canvas.after_idle(sync_scrollregion)
    except Exception:
        pass


def _qilabs_v06_patch_sidebar_scroll_for_class(cls):
    original = getattr(cls, "build_sidebar", None)
    if original is None or getattr(original, "_qilabs_v06_patched", False):
        return

    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        _qilabs_v06_enable_sidebar_scroll(self)
        return result

    wrapped._qilabs_v06_patched = True
    setattr(cls, "build_sidebar", wrapped)


try:
    _qilabs_v06_patch_sidebar_scroll_for_class(QiLabsToolbox)
except NameError:
    try:
        _qilabs_v06_patch_sidebar_scroll_for_class(QiOneShell)
    except NameError:
        pass
# --- END QILABS V0.6 SIDEBAR SCROLL PATCH ---
if __name__ == "__main__":
    QiLabsToolbox().mainloop()
