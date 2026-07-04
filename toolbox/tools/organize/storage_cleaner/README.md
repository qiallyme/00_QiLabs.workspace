        # Storage Cleaner

        **Group**: `tools/organize/`  
        **Migrated from**: `_archive/`

        ## Description

        Identifies and removes storage bloat: temp files, build artifacts, empty folders, and large redundant files across QiLabs roots.

        ## Files

        - `storage_cleaner.py`
        - `manifest.yaml`
        - `README.md`
        - `__init__.py`
        - `launch_storage_cleaner.bat`

        ## Tags

        `organize`, `clean`, `storage`, `bloat`, `delete`

        ## Safety

        [OK] Dry-run supported
[WARN] May delete files
[INFO] Review before live run recommended

        ## Usage

        Double-click `launch_storage_cleaner.bat` or run via the QiLabs Toolbox UI.

        ```
        python storage_cleaner.py
        ```
