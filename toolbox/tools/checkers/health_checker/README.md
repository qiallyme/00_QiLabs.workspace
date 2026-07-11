        # Health Checker

        **Group**: `tools/system/`  
        **Migrated from**: `_archive/`

        ## Description

        Checks the health and status of QiLabs workers, services, and background agents. Reports on active, idle, and failed processes.

        ## Files

        - `health_checker.py`
- `health_check_workers.py`
- `health_check_worker_status.py`
        - `manifest.yaml`
        - `README.md`
        - `__init__.py`
        - `launch_health_checker.bat`

        ## Tags

        `system`, `connector`, `health`, `workers`, `monitoring`

        ## Safety

        [OK] Read-only - no file changes

        ## Usage

        Double-click `launch_health_checker.bat` or run via the QiLabs Toolbox UI.

        ```
        python health_checker.py
        ```
