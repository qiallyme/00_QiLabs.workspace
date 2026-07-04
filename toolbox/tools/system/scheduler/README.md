        # Scheduler

        **Group**: `tools/system/`  
        **Migrated from**: `_archive/`

        ## Description

        Loads and manages scheduled task queues for QiLabs automation. Supports cron-style scheduling and on-demand queue processing.

        ## Files

        - `scheduler.py`
        - `manifest.yaml`
        - `README.md`
        - `__init__.py`
        - `launch_scheduler.bat`

        ## Tags

        `system`, `connector`, `scheduler`, `queue`, `automation`

        ## Safety

        [OK] Dry-run supported
[WARN] Modifies files
[INFO] Review before live run recommended

        ## Usage

        Double-click `launch_scheduler.bat` or run via the QiLabs Toolbox UI.

        ```
        python scheduler.py
        ```
