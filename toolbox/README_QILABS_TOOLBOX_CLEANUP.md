# QiLabs Toolbox Cleanup Script

Copy `cleanup_toolbox_folder.ps1` into:

```txt
C:\QiLabs\00_QiLabs.workspace\toolbox
```

Run preview first:

```powershell
Set-Location "C:\QiLabs\00_QiLabs.workspace\toolbox"
powershell -ExecutionPolicy Bypass -File .\cleanup_toolbox_folder.ps1
```

Apply cleanup:

```powershell
Set-Location "C:\QiLabs\00_QiLabs.workspace\toolbox"
powershell -ExecutionPolicy Bypass -File .\cleanup_toolbox_folder.ps1 -Apply
```

Apply and stop toolbox/python background processes first:

```powershell
Set-Location "C:\QiLabs\00_QiLabs.workspace\toolbox"
powershell -ExecutionPolicy Bypass -File .\cleanup_toolbox_folder.ps1 -Apply -StopToolboxProcesses
```

The script archives clutter into:

```txt
C:\QiLabs\00_QiLabs.workspace\toolbox\_archive\cleanup-YYYYMMDD-HHMMSS
```

It does not delete active tools or source code.
