# QiLabs Toolbox

QiLabs Toolbox is now a standalone Windows shell plus a runtime plugin host. The pinned EXE owns the window, sidebar, search, workspace selector, shared console, status bar, validation, auto-fix, and plugin creation. Tools live outside the EXE under `tools/<category>/<plugin>/` and are discovered from manifests at runtime.

Adding or editing normal tools does not require rebuilding `QiLabsToolbox.exe`.

## Run

From this folder:

```powershell
py main_ui.py
```

Or launch the built shell:

```powershell
.\QiLabsToolbox.exe
```

## Build The Shell

```powershell
.\build_toolbox_runtime.ps1
```

The build script works from `C:\QiLabs\00_QiLabs.workspace\toolbox`, stops old toolbox processes, refreshes the plugin registry, builds a onefile windowed EXE with PyInstaller, and copies it to:

```txt
C:\QiLabs\00_QiLabs.workspace\toolbox\QiLabsToolbox.exe
```

## Plugin Layout

```txt
tools/
  system/
    plugin_host_demo/
      manifest.yaml
      plugin_host_demo.py
      README.md
      __init__.py
```

The loader scans `tools/<category>/<plugin>/` and ignores `_pending`, `__pycache__`, `.venv`, `node_modules`, `dist`, `build`, and archive folders.

## Manifest

New plugins should use `entry:`:

```yaml
plugin_id: system.plugin_host_demo
tool_id: system.plugin_host_demo
name: Plugin Host Demo
category: system
version: 0.1.0
enabled: true
description: Demonstrates a native interactive QiPlugin v2 view.
entry:
  type: plugin_v2
  target: plugin_host_demo.py
  class_name: QiPlugin
requirements:
```

Existing `launch:` manifests are still supported and normalized into registry records.

Supported entry types:

- `plugin_v2`: native interactive plugin class with `build_view(host, parent)`.
- `legacy_basetool`: old `BaseTool` class with `get_name()`, `build_ui(parent)`, and `execute(...)`.
- `script`: Python script with `main()` or top-level execution.
- `bat`: Windows batch file.
- `exe`: executable.

## QiPlugin v2

```python
class QiPlugin:
    plugin_id = "category.plugin_name"
    name = "Plugin Name"
    category = "category"
    description = "What this plugin does."

    def build_view(self, host, parent):
        pass

    def validate(self, host):
        pass

    def activate(self, host):
        pass

    def deactivate(self, host):
        pass
```

The host API exposes `log`, `error`, `set_status`, `get_workspace`, `set_workspace`, `open_url`, `open_file`, `open_folder`, `run_background`, `install_requirements`, `refresh_plugins`, and `validate_plugin`.

## Create And Validate

Use the left sidebar buttons in the app:

- `Refresh`: rebuilds `toolbox_registry.json` and reloads plugins.
- `Validate`: writes `toolbox_validation_report.md`.
- `Auto-Fix`: safely fills missing manifest metadata, creates README/init files, and writes detected requirements.
- `New Tool`: scaffolds a native plugin, legacy wrapper, or simple script plugin.

CLI helpers:

```powershell
py -m toolbox_core.plugin_registry .
py toolbox_autofix_manifest_issues.py --apply
```
