# Housekeeping UI Layout Fix Report

## Overview

The Housekeeping Console UI has been redesigned to eliminate the need for whole-window scrolling. The layout now places all core action controls in a static, always-visible compact command bar at the top, while moving the heavier detailed logs and outputs into a multi-tab Notebook with dedicated scrollbars.

---

## Changes

### 1. Files Changed
* [housekeeping_ui.py](file:///C:/QiLabs/00_QiLabs.workspace/toolbox/_housekeeping/housekeeping_ui.py)

### 2. Backup Paths
* [housekeeping_ui.py.bak_scroll_era](file:///C:/QiLabs/00_QiLabs.workspace/toolbox/_housekeeping/housekeeping_ui.py.bak_scroll_era)

### 3. Compile Result
Compilation succeeded with no errors using `py -m compileall`:
```txt
Listing 'c:\QiLabs\00_QiLabs.workspace\toolbox\_housekeeping'...
Compiling 'c:\QiLabs\00_QiLabs.workspace\toolbox\_housekeeping\housekeeping_ui.py'...
```

---

## New UI Layout Description

* **Standard Top Menubar**: 
  * **Run**: Contains preview/apply items for both Phase 1, Manual, and Advanced modes, alongside Undo and Exit options.
  * **Open**: Direct shortcuts to Open Summary, Summaries Folder, Reports Folder, Folder Plans, Manifests Folder, and the main Housekeeping folder itself.
  * **Safety**: Checkboxes to toggle filename renames, commit, and push behaviors, and a "Reset Safe Defaults" action.
* **Top Compact Command Bar**: 
  * Features a **Phase** dropdown selector, a **Manual Step** dropdown, and action buttons (`Preview`, `Approve`, `Undo`, `Cancel`, `Clear Log`, and `Refresh`). These controls remain fixed at the top of the window and do not require scrolling to access.
* **Middle Tabbed Notebook**:
  * **Summary**: Shows metadata, planned write/rename counts, and active preview info with a vertical scrollbar.
  * **Output Log**: Displays real-time console messages with a vertical scrollbar.
  * **Safety / Plan**: Hosts checkboxes for safety flags, a reset button, and a detailed text panel showing currently loaded plan files.

---

## Layout Check

* **Is whole-window scrolling required?**  
  **No.** The window uses a standard frame arrangement where the top bar and status bar are static, and only the scrollable text widgets inside the Notebook tabs expand.
* **Is Phase 1 safe run still the default?**  
  **Yes.** On startup, the Phase dropdown defaults to **Phase 1 - QiSpark frontmatter only**.
* **Are Advanced phases protected?**  
  **Yes.** The advanced phases (Renames, Indexes, Tree, Git manifest) are run as preview-only from the main command bar. If a user attempts to click **Approve** on an advanced preview-only phase, a warning dialog is displayed to advise using Manual Step Mode if they wish to apply changes.
* **Is reset safe defaults working?**  
  **Yes.** Restores all safety checkbuttons to `False`, phase to `Phase 1`, and step to `Normalize frontmatter`.
