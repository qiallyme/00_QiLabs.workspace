# QiLabs BAT Launcher

A small Python/Tkinter toolbox tool that scans `C:\QiLabs` for `.bat` files and creates a searchable button/menu launcher so you do not have to remember where every mini-tool lives.

## Install path

Put this folder here:

```txt
C:\QiLabs\00_QiLabs.workspace\toolbox\tools\system\bat_launcher\
```

Then run:

```txt
launch_bat_launcher.bat
```

## What it does

- Scans only configured QiLabs roots, defaulting to `C:\QiLabs`.
- Builds `bat_registry.json`.
- Shows a searchable table of BAT tools.
- Lets you run the selected BAT in a new console window.
- Keeps the console open so you can watch verbose output.
- Logs launched BAT files to `logs/bat_launcher_runs.jsonl`.
- Warns on risky patterns like `format`, `diskpart`, `del /s`, `rmdir /s`, and encoded PowerShell.

## Nice labels

Add comments at the top of BAT files for better UI labels:

```bat
REM Tool: Housekeeping Console
REM Description: Opens the QiLabs housekeeping review/apply UI.
REM Category: housekeeping
```

The launcher will use those instead of the raw filename.

## Safety note

This is a launcher, not a sandbox. It warns and confirms, but the BAT file still does whatever the BAT file says. Keep confirmation enabled unless you are intentionally speed-running your own chaos.
