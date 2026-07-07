# Android USB Maintenance Toolkit

This folder contains a local Windows ADB setup for maintaining an Android phone over USB-C.

## One-Click Launcher

Run:

```powershell
.\AndroidTools.exe
```

The launcher scans for connected Android devices, shows their ADB state, lists apps, starts scrcpy, captures backups, and wraps package maintenance actions.

If Windows can see the phone for file transfer but ADB cannot see it, the launcher shows it as `Windows ... [mtp-only]`. That means USB debugging is not authorized yet, so app tools cannot run until Android shows as ADB state `device`.

To rebuild the launcher after source changes:

```powershell
.\Build-AndroidToolsLauncher.ps1
```

Installed tool:

- `tools/platform-tools/adb.exe`
- `tools/platform-tools/fastboot.exe`
- `tools/scrcpy/scrcpy.exe`

Google's Android documentation describes ADB as the command-line tool for communicating with an Android device. ADB over USB requires USB debugging to be enabled on the phone and the RSA authorization prompt accepted on the phone screen.

## First Connection

1. Plug the phone into the PC with a USB-C data cable.
2. On the phone, enable Developer Options:
   - Settings > About phone > tap Build number 7 times.
3. Enable USB debugging:
   - Settings > System > Developer options > USB debugging.
4. When the phone asks whether to allow USB debugging from this computer, choose Allow.
5. From this folder, run:

```powershell
.\Start-AndroidTools.ps1
.\scripts\Connect-Device.ps1
```

Once the device shows as `device`, you can mirror/control the phone from the PC:

```powershell
.\scripts\Start-Scrcpy.ps1
```

If PowerShell blocks scripts, run them like this:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Connect-Device.ps1
```

## Recommended Cleanup Flow

1. Capture the device state before changing anything:

```powershell
.\scripts\Backup-AndroidState.ps1
```

2. List third-party apps:

```powershell
.\scripts\List-Apps.ps1 -ThirdParty
```

3. Search for a suspicious package:

```powershell
.\scripts\List-Apps.ps1 -ThirdParty -Search suspicious
```

4. Disable the app first. This is usually reversible:

```powershell
.\scripts\Disable-App.ps1 -Package com.example.badapp
```

5. If the phone works better after disabling it, uninstall it for the current Android user:

```powershell
.\scripts\Uninstall-AppForUser.ps1 -Package com.example.badapp
```

6. If you disabled the wrong package, re-enable it:

```powershell
.\scripts\Enable-App.ps1 -Package com.example.package
```

7. If you uninstalled a built-in package for the current user and need it back:

```powershell
.\scripts\Install-Existing-App.ps1 -Package com.example.package
```

## Important Limits

- ADB cannot bypass the Android lock screen or the USB debugging authorization prompt.
- If the phone is too hard to use, try Android Safe Mode or connect a USB mouse/keyboard through a USB-C hub so you can approve the prompt.
- Do not disable or uninstall random system packages. Start with `-ThirdParty`, then research exact package names.
- Some malicious apps register as device administrators. If uninstall fails, check Settings > Security > Device admin apps and deactivate the app there first.
- `Uninstall-AppForUser.ps1` uses Android's per-user uninstall. For many built-in apps, that hides/removes the app for user `0` without deleting the APK from the system partition.

## Reports

The backup script writes timestamped reports under:

```text
reports/
```

Keep those files until the phone is stable. They make it much easier to reverse a bad change.

## Installed Sources

- Android SDK Platform Tools: Google Android Developers standalone Platform Tools download.
- scrcpy: official Genymobile GitHub release `scrcpy-win64-v4.0.zip`; SHA-256 verified during install.
