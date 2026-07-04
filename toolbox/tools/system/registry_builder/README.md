        # Registry Builder

        **Group**: `tools/system/`  
        **Migrated from**: `_archive/`

        ## Description

        Builds Windows registry files (.reg) from structured configuration templates for system deployment and setup automation.

        ## Files

        - `registry_builder.py`
        - `manifest.yaml`
        - `README.md`
        - `__init__.py`
        - `launch_registry_builder.bat`

        ## Tags

        `system`, `connector`, `registry`, `windows`, `deployment`

        ## Safety

        [OK] Dry-run supported
[WARN] Modifies files
[INFO] Review before live run recommended

        ## Usage

        Double-click `launch_registry_builder.bat` or run via the QiLabs Toolbox UI.

        ```
        python registry_builder.py
        ```
