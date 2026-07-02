from __future__ import annotations

import csv
import os
import subprocess
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CSV_FIELDS = ["group", "title", "url", "description", "tags", "priority", "enabled"]
DEFAULT_CSV = Path(__file__).with_name("bookmarks.csv")


@dataclass
class Bookmark:
    group: str = "General"
    title: str = ""
    url: str = ""
    description: str = ""
    tags: str = ""
    priority: str = "100"
    enabled: str = "true"

    @property
    def is_enabled(self) -> bool:
        return str(self.enabled).strip().lower() in {"1", "true", "yes", "y", "on"}

    @property
    def priority_int(self) -> int:
        try:
            return int(str(self.priority).strip())
        except Exception:
            return 100


def ensure_csv(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows([
            {"group": "Major Players", "title": "QiAccess", "url": "https://access.qially.com", "description": "Access/cockpit entry point.", "tags": "qiaccess,cockpit,major", "priority": "10", "enabled": "true"},
            {"group": "Major Players", "title": "QiSaysIt", "url": "https://qsaysit.com", "description": "Public writing site.", "tags": "public,writing,site", "priority": "20", "enabled": "true"},
            {"group": "Major Players", "title": "QiAlly", "url": "https://qially.com", "description": "Primary QiAlly hub.", "tags": "qially,public,major", "priority": "30", "enabled": "true"},
        ])


def load_bookmarks(path: Path) -> list[Bookmark]:
    ensure_csv(path)
    rows: list[Bookmark] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            if not raw:
                continue
            data = {field: (raw.get(field) or "").strip() for field in CSV_FIELDS}
            if not data["title"] and not data["url"]:
                continue
            rows.append(Bookmark(**data))
    return sorted(rows, key=lambda b: (b.group.lower(), b.priority_int, b.title.lower()))


def save_bookmarks(path: Path, bookmarks: list[Bookmark]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for bm in sorted(bookmarks, key=lambda b: (b.group.lower(), b.priority_int, b.title.lower())):
            writer.writerow(asdict(bm))
    tmp.replace(path)


def open_target(url: str) -> None:
    url = (url or "").strip()
    if not url:
        raise ValueError("This bookmark has no URL yet.")
    if url.lower().startswith(("http://", "https://", "file://", "mailto:")):
        webbrowser.open(url)
        return
    possible = Path(url)
    if possible.exists():
        if possible.is_dir() and os.name == "nt":
            subprocess.Popen(["explorer", str(possible)])
        else:
            webbrowser.open(possible.as_uri())
        return
    if "." in url and " " not in url:
        webbrowser.open("https://" + url)
        return
    webbrowser.open(url)


class QiPlugin:
    plugin_id = "access.qiaccess.bookmarks"
    name = "QiAccess Bookmarks"
    category = "access"
    description = "Local grouped bookmarks with CSV import/export."

    def __init__(self):
        self.csv_path = DEFAULT_CSV
        self.bookmarks: list[Bookmark] = []
        self.filtered: list[Bookmark] = []
        self.selected_index: int | None = None
        self.host = None
        self.form_vars: dict[str, tk.StringVar] = {}

    def validate(self, host):
        ensure_csv(self.csv_path)
        host.log(f"Bookmarks CSV OK: {self.csv_path}")

    def build_view(self, host, parent):
        self.host = host
        c = host.colors
        self.search_var = tk.StringVar()
        self.group_var = tk.StringVar(value="All")
        self.form_vars = {field: tk.StringVar() for field in CSV_FIELDS}
        self.form_vars["enabled"].set("true")
        self.form_vars["priority"].set("100")

        outer = tk.Frame(parent, bg=c["panel"])
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=c["panel"])
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="QiAccess Bookmarks", bg=c["panel"], fg=c["text"], font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(header, text="CSV source of truth", bg=c["panel"], fg=c["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(10, 0))

        body = tk.PanedWindow(outer, orient="horizontal", bg=c["panel"], sashwidth=6, bd=0)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=c["panel"], padx=0, pady=0)
        right = tk.Frame(body, bg=c["panel_2"], padx=10, pady=10, width=330)
        right.pack_propagate(False)
        body.add(left, minsize=520)
        body.add(right, minsize=285)

        controls = tk.Frame(left, bg=c["panel"])
        controls.pack(fill="x", pady=(0, 8))
        tk.Label(controls, text="Search", bg=c["panel"], fg=c["accent"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Entry(controls, textvariable=self.search_var, bg=c["panel_2"], fg=c["text"], insertbackground=c["text"], relief="flat", width=26).pack(side="left", padx=(6, 10), ipady=6)
        tk.Label(controls, text="Group", bg=c["panel"], fg=c["accent"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.group_combo = ttk.Combobox(controls, textvariable=self.group_var, state="readonly", width=20, values=["All"])
        self.group_combo.pack(side="left", padx=(6, 10))
        self._button(controls, "Open", self.open_selected, c["accent"], "#061014").pack(side="left", padx=(0, 6))
        self._button(controls, "Open Group", self.open_group, c["panel_3"], c["text"]).pack(side="left")

        columns = ("group", "title", "url", "tags", "priority", "enabled")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, text, width in [("group", "Group", 140), ("title", "Title", 190), ("url", "URL", 300), ("tags", "Tags", 150), ("priority", "#", 45), ("enabled", "On", 55)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda _e: self.open_selected())

        footer = tk.Frame(left, bg=c["panel"])
        footer.pack(fill="x", pady=(8, 0))
        for label, cmd in [("Reload", self.load_current_csv), ("Save", self.save_current_csv), ("Import", self.import_csv), ("Export", self.export_csv), ("Open CSV", self.open_csv_file), ("Folder", self.open_folder)]:
            self._button(footer, label, cmd, c["panel_3"], c["text"]).pack(side="left", padx=(0, 6))

        tk.Label(right, text="Edit Bookmark", bg=c["panel_2"], fg=c["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(right, text="Bulk edit in CSV when faster.", bg=c["panel_2"], fg=c["muted"], font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 8))
        for field in CSV_FIELDS:
            tk.Label(right, text=field.upper(), bg=c["panel_2"], fg=c["accent"], font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(6, 2))
            tk.Entry(right, textvariable=self.form_vars[field], bg=c["console_bg"], fg=c["text"], insertbackground=c["text"], relief="flat").pack(fill="x", ipady=6)

        row1 = tk.Frame(right, bg=c["panel_2"])
        row1.pack(fill="x", pady=(10, 0))
        self._button(row1, "New", self.clear_form, c["panel_3"], c["text"]).pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._button(row1, "Add", self.add_from_form, c["accent"], "#061014").pack(side="left", fill="x", expand=True, padx=4)
        self._button(row1, "Update", self.update_selected, c["accent"], "#061014").pack(side="left", fill="x", expand=True, padx=(4, 0))
        row2 = tk.Frame(right, bg=c["panel_2"])
        row2.pack(fill="x", pady=(6, 0))
        self._button(row2, "Duplicate", self.duplicate_selected, c["panel_3"], c["text"]).pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._button(row2, "Delete", self.delete_selected, c["danger"], "white").pack(side="left", fill="x", expand=True, padx=4)
        self._button(row2, "Copy URL", self.copy_url, c["panel_3"], c["text"]).pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.search_var.trace_add("write", lambda *_: self.refresh_view())
        self.group_var.trace_add("write", lambda *_: self.refresh_view())
        self.load_current_csv()

    def _button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", bd=0, padx=9, pady=6, cursor="hand2", font=("Segoe UI", 8, "bold"))

    def log(self, msg: str):
        if self.host:
            self.host.log(msg)

    def load_current_csv(self):
        try:
            self.bookmarks = load_bookmarks(self.csv_path)
            self.refresh_groups()
            self.refresh_view()
            self.log(f"Loaded {len(self.bookmarks)} bookmarks")
        except Exception as exc:
            messagebox.showerror("Load Failed", str(exc))

    def save_current_csv(self):
        save_bookmarks(self.csv_path, self.bookmarks)
        self.log(f"Saved {len(self.bookmarks)} bookmarks")

    def refresh_groups(self):
        groups = ["All"] + sorted({b.group for b in self.bookmarks if b.group})
        self.group_combo.configure(values=groups)
        if self.group_var.get() not in groups:
            self.group_var.set("All")

    def refresh_view(self):
        search = self.search_var.get().strip().lower()
        group = self.group_var.get().strip()
        self.filtered = []
        for b in self.bookmarks:
            hay = " ".join([b.group, b.title, b.url, b.description, b.tags]).lower()
            if group != "All" and b.group != group:
                continue
            if search and search not in hay:
                continue
            self.filtered.append(b)
        self.tree.delete(*self.tree.get_children())
        for idx, b in enumerate(self.filtered):
            self.tree.insert("", "end", iid=str(idx), values=(b.group, b.title, b.url, b.tags, b.priority, "yes" if b.is_enabled else "no"))

    def selected_bookmark(self) -> Bookmark | None:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        return self.filtered[idx] if 0 <= idx < len(self.filtered) else None

    def on_select(self, _event=None):
        b = self.selected_bookmark()
        if not b:
            return
        self.selected_index = self.bookmarks.index(b)
        for field in CSV_FIELDS:
            self.form_vars[field].set(getattr(b, field))

    def form_bookmark(self) -> Bookmark:
        return Bookmark(**{field: self.form_vars[field].get().strip() for field in CSV_FIELDS})

    def clear_form(self):
        for field in CSV_FIELDS:
            self.form_vars[field].set("")
        self.form_vars["group"].set("General")
        self.form_vars["priority"].set("100")
        self.form_vars["enabled"].set("true")
        self.selected_index = None

    def add_from_form(self):
        b = self.form_bookmark()
        if not b.title and not b.url:
            messagebox.showwarning("Missing bookmark", "Add a title or URL first.")
            return
        self.bookmarks.append(b)
        self.save_current_csv()
        self.refresh_groups()
        self.refresh_view()

    def update_selected(self):
        if self.selected_index is None:
            messagebox.showinfo("No selection", "Select a bookmark first.")
            return
        self.bookmarks[self.selected_index] = self.form_bookmark()
        self.save_current_csv()
        self.refresh_groups()
        self.refresh_view()

    def duplicate_selected(self):
        b = self.selected_bookmark()
        if not b:
            return
        dup = Bookmark(**asdict(b))
        dup.title = dup.title + " Copy"
        self.bookmarks.append(dup)
        self.save_current_csv()
        self.refresh_groups()
        self.refresh_view()

    def delete_selected(self):
        b = self.selected_bookmark()
        if not b:
            return
        if messagebox.askyesno("Delete", f"Delete {b.title or b.url}?"):
            self.bookmarks.remove(b)
            self.save_current_csv()
            self.refresh_groups()
            self.refresh_view()
            self.clear_form()

    def open_selected(self):
        b = self.selected_bookmark()
        if not b:
            messagebox.showinfo("No selection", "Select a bookmark first.")
            return
        open_target(b.url)

    def open_group(self):
        group = self.group_var.get()
        opened = 0
        for b in self.bookmarks:
            if b.is_enabled and (group == "All" or b.group == group):
                open_target(b.url)
                opened += 1
        self.log(f"Opened {opened} bookmarks")

    def copy_url(self):
        b = self.selected_bookmark()
        if not b:
            return
        self.tree.clipboard_clear()
        self.tree.clipboard_append(b.url)
        self.log("Copied URL")

    def import_csv(self):
        path = filedialog.askopenfilename(title="Import bookmarks CSV", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        self.bookmarks = load_bookmarks(Path(path))
        self.save_current_csv()
        self.refresh_groups()
        self.refresh_view()

    def export_csv(self):
        path = filedialog.asksaveasfilename(title="Export bookmarks CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            save_bookmarks(Path(path), self.bookmarks)
            self.log(f"Exported {path}")

    def open_csv_file(self):
        if self.host:
            self.host.open_file(str(self.csv_path))

    def open_folder(self):
        if self.host:
            self.host.open_folder(str(self.csv_path.parent))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("QiAccess Bookmarks")
    plugin = QiPlugin()
    class _Host:
        colors = {"panel":"#151f2b","panel_2":"#1b2937","panel_3":"#26384a","console_bg":"#061019","text":"#f4f7fb","muted":"#9aabba","accent":"#65dbc8","danger":"#ff6b7a"}
        def log(self, m): print(m)
        def open_file(self, p): os.startfile(p)
        def open_folder(self, p): os.startfile(p)
    plugin.build_view(_Host(), root)
    root.mainloop()
