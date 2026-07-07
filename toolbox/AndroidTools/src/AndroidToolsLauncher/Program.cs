using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Management;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace AndroidToolsLauncher
{
    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            var appRoot = AppDomain.CurrentDomain.BaseDirectory;
            if (args.Any(a => string.Equals(a, "--self-test", StringComparison.OrdinalIgnoreCase)))
            {
                var adb = Path.Combine(appRoot, "tools", "platform-tools", "adb.exe");
                var scrcpy = Path.Combine(appRoot, "tools", "scrcpy", "scrcpy.exe");
                return File.Exists(adb) && File.Exists(scrcpy) ? 0 : 1;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm(appRoot));
            return 0;
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly string appRoot;
        private readonly string adbPath;
        private readonly string scrcpyPath;
        private readonly string reportsPath;
        private readonly Timer refreshTimer;

        private readonly ComboBox deviceCombo = new ComboBox();
        private readonly Button refreshDevicesButton = new Button();
        private readonly Button restartAdbButton = new Button();
        private readonly Button backupButton = new Button();
        private readonly Button scrcpyButton = new Button();
        private readonly Button reportsButton = new Button();
        private readonly Label deviceStatusLabel = new Label();

        private readonly CheckBox thirdPartyCheck = new CheckBox();
        private readonly CheckBox systemCheck = new CheckBox();
        private readonly CheckBox disabledCheck = new CheckBox();
        private readonly CheckBox enabledCheck = new CheckBox();
        private readonly TextBox searchText = new TextBox();
        private readonly Button listAppsButton = new Button();
        private readonly DataGridView packagesGrid = new DataGridView();
        private readonly TextBox selectedPackageText = new TextBox();
        private readonly Button disableButton = new Button();
        private readonly Button enableButton = new Button();
        private readonly Button uninstallButton = new Button();
        private readonly Button restoreButton = new Button();
        private readonly Button packagePathButton = new Button();
        private readonly TextBox logBox = new TextBox();

        private List<DeviceInfo> devices = new List<DeviceInfo>();
        private List<PackageInfo> packages = new List<PackageInfo>();
        private bool refreshingDevices;
        private bool runningCommand;

        public MainForm(string appRoot)
        {
            this.appRoot = appRoot;
            adbPath = Path.Combine(appRoot, "tools", "platform-tools", "adb.exe");
            scrcpyPath = Path.Combine(appRoot, "tools", "scrcpy", "scrcpy.exe");
            reportsPath = Path.Combine(appRoot, "reports");

            Text = "Android Tools";
            MinimumSize = new Size(1000, 700);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 9F);

            BuildUi();
            WireEvents();

            refreshTimer = new Timer { Interval = 8000 };
            refreshTimer.Tick += async (sender, args) => await RefreshDevicesAsync(false);

            Shown += async (sender, args) =>
            {
                Log("Android Tools launcher ready.");
                Log("ADB: " + adbPath);
                Log("scrcpy: " + scrcpyPath);
                ValidateLocalTools();
                refreshTimer.Start();
                await RefreshDevicesAsync(true);
            };
        }

        private void BuildUi()
        {
            var root = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 4,
                ColumnCount = 1,
                Padding = new Padding(10)
            };
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 82));
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 82));
            root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 170));
            Controls.Add(root);

            var devicePanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 8,
                RowCount = 2
            };
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            devicePanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));
            devicePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            devicePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            root.Controls.Add(devicePanel, 0, 0);

            var deviceLabel = new Label
            {
                Text = "Device",
                TextAlign = ContentAlignment.MiddleLeft,
                Dock = DockStyle.Fill
            };
            devicePanel.Controls.Add(deviceLabel, 0, 0);

            deviceCombo.Dock = DockStyle.Fill;
            deviceCombo.DropDownStyle = ComboBoxStyle.DropDownList;
            devicePanel.Controls.Add(deviceCombo, 1, 0);

            ConfigureButton(refreshDevicesButton, "Refresh");
            ConfigureButton(restartAdbButton, "Restart ADB");
            ConfigureButton(backupButton, "Backup");
            ConfigureButton(scrcpyButton, "scrcpy");
            ConfigureButton(reportsButton, "Reports");
            devicePanel.Controls.Add(refreshDevicesButton, 2, 0);
            devicePanel.Controls.Add(restartAdbButton, 3, 0);
            devicePanel.Controls.Add(backupButton, 4, 0);
            devicePanel.Controls.Add(scrcpyButton, 5, 0);
            devicePanel.Controls.Add(reportsButton, 6, 0);

            deviceStatusLabel.Text = "No device scan yet.";
            deviceStatusLabel.TextAlign = ContentAlignment.MiddleLeft;
            deviceStatusLabel.Dock = DockStyle.Fill;
            devicePanel.SetColumnSpan(deviceStatusLabel, 8);
            devicePanel.Controls.Add(deviceStatusLabel, 0, 1);

            var filterPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 9,
                RowCount = 2
            };
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 110));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 110));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 70));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            filterPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
            filterPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            filterPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            root.Controls.Add(filterPanel, 0, 1);

            ConfigureCheck(thirdPartyCheck, "Third-party", true);
            ConfigureCheck(systemCheck, "System", false);
            ConfigureCheck(disabledCheck, "Disabled", false);
            ConfigureCheck(enabledCheck, "Enabled", false);
            filterPanel.Controls.Add(thirdPartyCheck, 0, 0);
            filterPanel.Controls.Add(systemCheck, 1, 0);
            filterPanel.Controls.Add(disabledCheck, 2, 0);
            filterPanel.Controls.Add(enabledCheck, 3, 0);

            var searchLabel = new Label
            {
                Text = "Search",
                TextAlign = ContentAlignment.MiddleLeft,
                Dock = DockStyle.Fill
            };
            filterPanel.Controls.Add(searchLabel, 4, 0);

            searchText.Dock = DockStyle.Fill;
            filterPanel.Controls.Add(searchText, 5, 0);

            ConfigureButton(listAppsButton, "List Apps");
            filterPanel.Controls.Add(listAppsButton, 6, 0);

            var selectedLabel = new Label
            {
                Text = "Selected package",
                TextAlign = ContentAlignment.MiddleLeft,
                Dock = DockStyle.Fill
            };
            filterPanel.Controls.Add(selectedLabel, 0, 1);

            selectedPackageText.Dock = DockStyle.Fill;
            filterPanel.SetColumnSpan(selectedPackageText, 5);
            filterPanel.Controls.Add(selectedPackageText, 1, 1);

            ConfigureButton(packagePathButton, "Package Path");
            filterPanel.Controls.Add(packagePathButton, 6, 1);

            packagesGrid.Dock = DockStyle.Fill;
            packagesGrid.AllowUserToAddRows = false;
            packagesGrid.AllowUserToDeleteRows = false;
            packagesGrid.ReadOnly = true;
            packagesGrid.RowHeadersVisible = false;
            packagesGrid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            packagesGrid.MultiSelect = false;
            packagesGrid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            packagesGrid.Columns.Add("Package", "Package");
            packagesGrid.Columns.Add("Installer", "Installer");
            packagesGrid.Columns.Add("Uid", "UID");
            packagesGrid.Columns.Add("Path", "Path");
            packagesGrid.Columns["Package"].FillWeight = 160;
            packagesGrid.Columns["Installer"].FillWeight = 110;
            packagesGrid.Columns["Uid"].FillWeight = 55;
            packagesGrid.Columns["Path"].FillWeight = 220;
            root.Controls.Add(packagesGrid, 0, 2);

            var bottom = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                RowCount = 1
            };
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 500));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            root.Controls.Add(bottom, 0, 3);

            var actionPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                RowCount = 4
            };
            actionPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
            actionPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
            actionPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            actionPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            actionPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            actionPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
            bottom.Controls.Add(actionPanel, 0, 0);

            ConfigureButton(disableButton, "Disable");
            ConfigureButton(enableButton, "Enable");
            ConfigureButton(uninstallButton, "Uninstall for User");
            ConfigureButton(restoreButton, "Restore Existing");
            actionPanel.Controls.Add(disableButton, 0, 0);
            actionPanel.Controls.Add(enableButton, 1, 0);
            actionPanel.Controls.Add(uninstallButton, 0, 1);
            actionPanel.Controls.Add(restoreButton, 1, 1);

            var hint = new Label
            {
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                Text = "Use Disable first. Uninstall-for-user is next if the phone improves.",
                AutoSize = false
            };
            actionPanel.SetColumnSpan(hint, 2);
            actionPanel.Controls.Add(hint, 0, 2);

            var hint2 = new Label
            {
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                Text = "Authorized state must be 'device'. 'unauthorized' means approve the phone prompt.",
                AutoSize = false
            };
            actionPanel.SetColumnSpan(hint2, 2);
            actionPanel.Controls.Add(hint2, 0, 3);

            logBox.Dock = DockStyle.Fill;
            logBox.Multiline = true;
            logBox.ReadOnly = true;
            logBox.ScrollBars = ScrollBars.Both;
            logBox.WordWrap = false;
            logBox.Font = new Font("Consolas", 9F);
            bottom.Controls.Add(logBox, 1, 0);
        }

        private void WireEvents()
        {
            refreshDevicesButton.Click += async (sender, args) => await RefreshDevicesAsync(true);
            restartAdbButton.Click += async (sender, args) => await RestartAdbAsync();
            backupButton.Click += async (sender, args) => await BackupStateAsync();
            scrcpyButton.Click += (sender, args) => StartScrcpy();
            reportsButton.Click += (sender, args) => OpenReports();
            listAppsButton.Click += async (sender, args) => await ListPackagesAsync();
            searchText.TextChanged += (sender, args) => ApplyPackageSearch();

            packagesGrid.SelectionChanged += (sender, args) =>
            {
                if (packagesGrid.SelectedRows.Count == 0)
                {
                    return;
                }

                var row = packagesGrid.SelectedRows[0];
                var package = Convert.ToString(row.Cells["Package"].Value);
                if (!string.IsNullOrWhiteSpace(package))
                {
                    selectedPackageText.Text = package;
                }
            };

            disableButton.Click += async (sender, args) =>
                await RunPackageActionAsync("disable for Android user 0", true, "shell", "pm", "disable-user", "--user", "0");

            enableButton.Click += async (sender, args) =>
                await RunPackageActionAsync("enable", false, "shell", "pm", "enable");

            uninstallButton.Click += async (sender, args) =>
                await RunPackageActionAsync("uninstall for Android user 0", true, "shell", "pm", "uninstall", "--user", "0");

            restoreButton.Click += async (sender, args) => await RestoreExistingPackageAsync();
            packagePathButton.Click += async (sender, args) => await ShowPackagePathAsync();
        }

        private void ConfigureButton(Button button, string text)
        {
            button.Text = text;
            button.Dock = DockStyle.Fill;
            button.Margin = new Padding(4);
            button.AutoEllipsis = true;
        }

        private void ConfigureCheck(CheckBox box, string text, bool isChecked)
        {
            box.Text = text;
            box.Checked = isChecked;
            box.Dock = DockStyle.Fill;
            box.TextAlign = ContentAlignment.MiddleLeft;
        }

        private void ValidateLocalTools()
        {
            if (!File.Exists(adbPath))
            {
                Log("ERROR: adb.exe was not found. Expected: " + adbPath);
            }

            if (!File.Exists(scrcpyPath))
            {
                Log("WARNING: scrcpy.exe was not found. Screen control will be unavailable.");
            }
        }

        private async Task RefreshDevicesAsync(bool userRequested)
        {
            if (refreshingDevices || !File.Exists(adbPath))
            {
                return;
            }

            refreshingDevices = true;
            refreshDevicesButton.Enabled = false;

            try
            {
                if (userRequested)
                {
                    Log("Scanning for connected Android devices...");
                }

                var result = await Task.Run(() => RunAdb(15000, "devices", "-l"));
                if (result.ExitCode != 0)
                {
                    LogResult("adb devices failed", result);
                    deviceStatusLabel.Text = "ADB device scan failed.";
                    return;
                }

                var previousSerial = SelectedSerialOrEmpty();
                var adbDevices = ParseDevices(result.Output).ToList();
                var windowsDevices = GetWindowsPortableDevices()
                    .Where(w => !adbDevices.Any(a => ContainsIgnoreCase(w.Serial, a.Serial) || ContainsIgnoreCase(w.Details, a.Serial)))
                    .ToList();

                devices = adbDevices.Concat(windowsDevices).ToList();
                deviceCombo.Items.Clear();

                foreach (var device in devices)
                {
                    deviceCombo.Items.Add(device);
                }

                if (deviceCombo.Items.Count > 0)
                {
                    var previous = devices.FindIndex(d => d.Serial == previousSerial);
                    var firstReady = devices.FindIndex(d => d.State == "device");
                    deviceCombo.SelectedIndex = previous >= 0 ? previous : (firstReady >= 0 ? firstReady : 0);
                }

                var readyCount = devices.Count(d => d.Source == "ADB" && d.State == "device");
                var unauthorizedCount = devices.Count(d => d.Source == "ADB" && d.State == "unauthorized");
                var mtpOnlyCount = devices.Count(d => d.State == "mtp-only");

                if (devices.Count == 0)
                {
                    deviceStatusLabel.Text = "No Android devices detected by ADB or Windows Portable Devices.";
                }
                else
                {
                    deviceStatusLabel.Text = string.Format(
                        "Detected {0} device(s). ADB ready: {1}. Unauthorized: {2}. Windows/MTP only: {3}.",
                        devices.Count,
                        readyCount,
                        unauthorizedCount,
                        mtpOnlyCount);
                }

                if (userRequested)
                {
                    Log(deviceStatusLabel.Text);
                    if (unauthorizedCount > 0)
                    {
                        Log("Unlock the phone and approve the USB debugging prompt.");
                    }
                    if (mtpOnlyCount > 0 && readyCount == 0)
                    {
                        Log("Windows sees a phone, but ADB does not. Enable Developer options > USB debugging, then accept the RSA prompt.");
                    }
                }
            }
            finally
            {
                refreshDevicesButton.Enabled = true;
                refreshingDevices = false;
            }
        }

        private async Task RestartAdbAsync()
        {
            await RunGuardedAsync("Restarting ADB server...", async () =>
            {
                var kill = await Task.Run(() => RunAdb(15000, "kill-server"));
                LogResult("adb kill-server", kill);

                var start = await Task.Run(() => RunAdb(15000, "start-server"));
                LogResult("adb start-server", start);

                await RefreshDevicesAsync(true);
            });
        }

        private async Task ListPackagesAsync()
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            await RunGuardedAsync("Listing packages on " + device.Serial + "...", async () =>
            {
                var args = new List<string> { "-s", device.Serial, "shell", "pm", "list", "packages", "-f", "-i", "-U" };
                if (thirdPartyCheck.Checked)
                {
                    args.Add("-3");
                }
                if (systemCheck.Checked)
                {
                    args.Add("-s");
                }
                if (disabledCheck.Checked)
                {
                    args.Add("-d");
                }
                if (enabledCheck.Checked)
                {
                    args.Add("-e");
                }

                var result = await Task.Run(() => RunAdb(60000, args.ToArray()));
                if (result.ExitCode != 0)
                {
                    LogResult("pm list packages failed", result);
                    return;
                }

                packages = ParsePackages(result.Output).OrderBy(p => p.Package).ToList();
                ApplyPackageSearch();
                Log("Loaded " + packages.Count + " package(s).");
            });
        }

        private void ApplyPackageSearch()
        {
            var needle = searchText.Text.Trim();
            var rows = packages.AsEnumerable();
            if (needle.Length > 0)
            {
                rows = rows.Where(p =>
                    ContainsIgnoreCase(p.Package, needle) ||
                    ContainsIgnoreCase(p.Installer, needle) ||
                    ContainsIgnoreCase(p.Path, needle));
            }

            packagesGrid.Rows.Clear();
            foreach (var package in rows)
            {
                packagesGrid.Rows.Add(package.Package, package.Installer, package.Uid, package.Path);
            }
        }

        private async Task BackupStateAsync()
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            await RunGuardedAsync("Backing up device state for " + device.Serial + "...", async () =>
            {
                Directory.CreateDirectory(reportsPath);
                var dir = Path.Combine(reportsPath, "device-state-" + DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.CreateDirectory(dir);

                await SaveAdbOutputAsync(Path.Combine(dir, "adb-devices.txt"), 30000, "devices", "-l");
                await SaveAdbOutputAsync(Path.Combine(dir, "getprop.txt"), 30000, "-s", device.Serial, "shell", "getprop");
                await SaveAdbOutputAsync(Path.Combine(dir, "users.txt"), 30000, "-s", device.Serial, "shell", "pm", "list", "users");
                await SaveAdbOutputAsync(Path.Combine(dir, "packages-all.txt"), 60000, "-s", device.Serial, "shell", "pm", "list", "packages", "-f", "-i", "-U");
                await SaveAdbOutputAsync(Path.Combine(dir, "packages-third-party.txt"), 60000, "-s", device.Serial, "shell", "pm", "list", "packages", "-3", "-f", "-i", "-U");
                await SaveAdbOutputAsync(Path.Combine(dir, "packages-disabled.txt"), 60000, "-s", device.Serial, "shell", "pm", "list", "packages", "-d", "-f", "-i", "-U");
                await SaveAdbOutputAsync(Path.Combine(dir, "device-policy.txt"), 60000, "-s", device.Serial, "shell", "dumpsys", "device_policy");

                Log("Backup saved: " + dir);
                Process.Start("explorer.exe", QuoteArg(dir));
            });
        }

        private async Task SaveAdbOutputAsync(string path, int timeoutMs, params string[] args)
        {
            var result = await Task.Run(() => RunAdb(timeoutMs, args));
            var text = result.Output;
            if (result.ExitCode != 0)
            {
                text = "Exit code: " + result.ExitCode + Environment.NewLine + text;
            }

            File.WriteAllText(path, text, Encoding.UTF8);
        }

        private async Task RunPackageActionAsync(string action, bool requireExactConfirmation, params string[] baseArgs)
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            var package = selectedPackageText.Text.Trim();
            if (package.Length == 0)
            {
                MessageBox.Show(this, "Select or type a package name first.", "Package Required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            if (requireExactConfirmation && !ConfirmPackage(package, action))
            {
                Log("Cancelled " + action + " for " + package + ".");
                return;
            }

            await RunGuardedAsync("Running " + action + " for " + package + "...", async () =>
            {
                var args = new List<string> { "-s", device.Serial };
                args.AddRange(baseArgs);
                args.Add(package);

                var result = await Task.Run(() => RunAdb(60000, args.ToArray()));
                LogResult(action + " " + package, result);
            });
        }

        private async Task RestoreExistingPackageAsync()
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            var package = selectedPackageText.Text.Trim();
            if (package.Length == 0)
            {
                MessageBox.Show(this, "Select or type a package name first.", "Package Required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            await RunGuardedAsync("Restoring existing package " + package + "...", async () =>
            {
                var install = await Task.Run(() => RunAdb(60000, "-s", device.Serial, "shell", "cmd", "package", "install-existing", "--user", "0", package));
                LogResult("install-existing " + package, install);

                var enable = await Task.Run(() => RunAdb(60000, "-s", device.Serial, "shell", "pm", "enable", package));
                LogResult("enable " + package, enable);
            });
        }

        private async Task ShowPackagePathAsync()
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            var package = selectedPackageText.Text.Trim();
            if (package.Length == 0)
            {
                MessageBox.Show(this, "Select or type a package name first.", "Package Required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            await RunGuardedAsync("Checking package path for " + package + "...", async () =>
            {
                var result = await Task.Run(() => RunAdb(30000, "-s", device.Serial, "shell", "pm", "path", package));
                LogResult("pm path " + package, result);
            });
        }

        private void StartScrcpy()
        {
            var device = GetReadyDevice();
            if (device == null)
            {
                return;
            }

            if (!File.Exists(scrcpyPath))
            {
                MessageBox.Show(this, "scrcpy.exe was not found at " + scrcpyPath, "Missing scrcpy", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = scrcpyPath,
                    Arguments = "--serial " + QuoteArg(device.Serial),
                    WorkingDirectory = Path.GetDirectoryName(scrcpyPath),
                    UseShellExecute = false
                };
                startInfo.EnvironmentVariables["PATH"] =
                    Path.Combine(appRoot, "tools", "platform-tools") + ";" +
                    Path.Combine(appRoot, "tools", "scrcpy") + ";" +
                    startInfo.EnvironmentVariables["PATH"];

                Process.Start(startInfo);
                Log("Started scrcpy for " + device.Serial + ".");
            }
            catch (Exception ex)
            {
                Log("Failed to start scrcpy: " + ex.Message);
                MessageBox.Show(this, ex.Message, "scrcpy Failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OpenReports()
        {
            Directory.CreateDirectory(reportsPath);
            Process.Start("explorer.exe", QuoteArg(reportsPath));
        }

        private async Task RunGuardedAsync(string startMessage, Func<Task> action)
        {
            if (runningCommand)
            {
                MessageBox.Show(this, "Another tool action is still running.", "Busy", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            runningCommand = true;
            SetActionButtons(false);
            Log(startMessage);

            try
            {
                await action();
            }
            catch (Exception ex)
            {
                Log("ERROR: " + ex.Message);
                MessageBox.Show(this, ex.Message, "Tool Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                runningCommand = false;
                SetActionButtons(true);
            }
        }

        private void SetActionButtons(bool enabled)
        {
            backupButton.Enabled = enabled;
            listAppsButton.Enabled = enabled;
            disableButton.Enabled = enabled;
            enableButton.Enabled = enabled;
            uninstallButton.Enabled = enabled;
            restoreButton.Enabled = enabled;
            packagePathButton.Enabled = enabled;
            restartAdbButton.Enabled = enabled;
            scrcpyButton.Enabled = enabled;
        }

        private DeviceInfo GetReadyDevice()
        {
            var selected = deviceCombo.SelectedItem as DeviceInfo;
            if (selected == null)
            {
                MessageBox.Show(this, "No Android device is selected. Click Refresh after plugging in the phone.", "No Device", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return null;
            }

            if (selected.State != "device")
            {
                string message;
                if (selected.State == "unauthorized")
                {
                    message = "The selected device is unauthorized. Unlock the phone and approve the USB debugging prompt.";
                }
                else if (selected.State == "mtp-only")
                {
                    message = "Windows can see this phone for file transfer, but ADB cannot see it yet. On the phone, enable Developer options > USB debugging, then approve the USB debugging RSA prompt.";
                }
                else
                {
                    message = "The selected device is not ready. Current ADB state: " + selected.State;
                }

                MessageBox.Show(this, message, "Device Not Ready", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return null;
            }

            return selected;
        }

        private string SelectedSerialOrEmpty()
        {
            var selected = deviceCombo.SelectedItem as DeviceInfo;
            return selected == null ? string.Empty : selected.Serial;
        }

        private bool ConfirmPackage(string package, string action)
        {
            using (var form = new Form())
            using (var label = new Label())
            using (var input = new TextBox())
            using (var ok = new Button())
            using (var cancel = new Button())
            {
                form.Text = "Confirm Package Action";
                form.StartPosition = FormStartPosition.CenterParent;
                form.FormBorderStyle = FormBorderStyle.FixedDialog;
                form.MinimizeBox = false;
                form.MaximizeBox = false;
                form.ClientSize = new Size(520, 160);
                form.Font = Font;

                label.Text = "About to " + action + ":" + Environment.NewLine + package + Environment.NewLine + "Type the exact package name to continue.";
                label.SetBounds(12, 12, 496, 62);

                input.SetBounds(12, 82, 496, 24);

                ok.Text = "Run";
                ok.Enabled = false;
                ok.DialogResult = DialogResult.OK;
                ok.SetBounds(332, 118, 84, 28);

                cancel.Text = "Cancel";
                cancel.DialogResult = DialogResult.Cancel;
                cancel.SetBounds(424, 118, 84, 28);

                input.TextChanged += (sender, args) => ok.Enabled = input.Text == package;

                form.Controls.Add(label);
                form.Controls.Add(input);
                form.Controls.Add(ok);
                form.Controls.Add(cancel);
                form.AcceptButton = ok;
                form.CancelButton = cancel;

                return form.ShowDialog(this) == DialogResult.OK;
            }
        }

        private CommandResult RunAdb(int timeoutMs, params string[] args)
        {
            return RunProcess(adbPath, args, timeoutMs, appRoot);
        }

        private CommandResult RunProcess(string fileName, string[] args, int timeoutMs, string workingDirectory)
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = JoinArguments(args),
                WorkingDirectory = workingDirectory,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };

            using (var process = new Process())
            {
                var stdout = new StringBuilder();
                var stderr = new StringBuilder();

                process.StartInfo = startInfo;
                process.OutputDataReceived += (sender, line) =>
                {
                    if (line.Data != null)
                    {
                        stdout.AppendLine(line.Data);
                    }
                };
                process.ErrorDataReceived += (sender, line) =>
                {
                    if (line.Data != null)
                    {
                        stderr.AppendLine(line.Data);
                    }
                };

                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                if (!process.WaitForExit(timeoutMs))
                {
                    try
                    {
                        process.Kill();
                    }
                    catch
                    {
                    }

                    return new CommandResult
                    {
                        ExitCode = -1,
                        Stdout = stdout.ToString(),
                        Stderr = stderr.ToString() + "Timed out after " + timeoutMs + "ms."
                    };
                }

                process.WaitForExit();
                return new CommandResult
                {
                    ExitCode = process.ExitCode,
                    Stdout = stdout.ToString(),
                    Stderr = stderr.ToString()
                };
            }
        }

        private IEnumerable<DeviceInfo> ParseDevices(string output)
        {
            using (var reader = new StringReader(output))
            {
                string line;
                while ((line = reader.ReadLine()) != null)
                {
                    line = line.Trim();
                    if (line.Length == 0 || line.StartsWith("List of devices", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    var parts = Regex.Split(line, "\\s+");
                    if (parts.Length < 2)
                    {
                        continue;
                    }

                    yield return new DeviceInfo
                    {
                        Serial = parts[0],
                        State = parts[1],
                        Details = parts.Length > 2 ? string.Join(" ", parts.Skip(2).ToArray()) : string.Empty,
                        Source = "ADB"
                    };
                }
            }
        }

        private IEnumerable<DeviceInfo> GetWindowsPortableDevices()
        {
            var devices = new List<DeviceInfo>();

            try
            {
                using (var searcher = new ManagementObjectSearcher("SELECT Name, PNPClass, PNPDeviceID, Status FROM Win32_PnPEntity WHERE PNPClass = 'WPD' OR Name LIKE '%Android%' OR Name LIKE '%Phone%' OR Name LIKE '%ADB%'"))
                using (var results = searcher.Get())
                {
                    foreach (ManagementObject item in results)
                    {
                        var name = Convert.ToString(item["Name"]);
                        var pnpClass = Convert.ToString(item["PNPClass"]);
                        var pnpId = Convert.ToString(item["PNPDeviceID"]);
                        var status = Convert.ToString(item["Status"]);

                        if (string.IsNullOrWhiteSpace(name) || string.IsNullOrWhiteSpace(pnpId))
                        {
                            continue;
                        }

                        if (!string.Equals(status, "OK", StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        if (!string.Equals(pnpClass, "WPD", StringComparison.OrdinalIgnoreCase) &&
                            name.IndexOf("Android", StringComparison.OrdinalIgnoreCase) < 0 &&
                            name.IndexOf("Phone", StringComparison.OrdinalIgnoreCase) < 0 &&
                            name.IndexOf("ADB", StringComparison.OrdinalIgnoreCase) < 0)
                        {
                            continue;
                        }

                        devices.Add(new DeviceInfo
                        {
                            Serial = pnpId,
                            State = "mtp-only",
                            Details = name,
                            Source = "Windows"
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                Log("Windows device scan failed: " + ex.Message);
            }

            return devices
                .GroupBy(d => d.Serial, StringComparer.OrdinalIgnoreCase)
                .Select(g => g.First())
                .OrderBy(d => d.Details)
                .ToList();
        }

        private IEnumerable<PackageInfo> ParsePackages(string output)
        {
            var regex = new Regex("^package:(?<path>.+?)=(?<package>\\S+)(?:\\s+installer=(?<installer>\\S+))?(?:\\s+uid:(?<uid>\\d+))?", RegexOptions.Compiled);

            using (var reader = new StringReader(output))
            {
                string line;
                while ((line = reader.ReadLine()) != null)
                {
                    line = line.Trim();
                    var match = regex.Match(line);
                    if (!match.Success)
                    {
                        continue;
                    }

                    yield return new PackageInfo
                    {
                        Package = match.Groups["package"].Value,
                        Installer = match.Groups["installer"].Success ? match.Groups["installer"].Value : string.Empty,
                        Uid = match.Groups["uid"].Success ? match.Groups["uid"].Value : string.Empty,
                        Path = match.Groups["path"].Value
                    };
                }
            }
        }

        private void LogResult(string label, CommandResult result)
        {
            Log(label + " -> exit " + result.ExitCode);
            var text = result.Output.Trim();
            if (text.Length > 0)
            {
                Log(text);
            }
        }

        private void Log(string message)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<string>(Log), message);
                return;
            }

            logBox.AppendText("[" + DateTime.Now.ToString("HH:mm:ss") + "] " + message + Environment.NewLine);
        }

        private static bool ContainsIgnoreCase(string text, string value)
        {
            return (text ?? string.Empty).IndexOf(value, StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static string JoinArguments(IEnumerable<string> args)
        {
            return string.Join(" ", args.Select(QuoteArg).ToArray());
        }

        private static string QuoteArg(string arg)
        {
            if (arg == null)
            {
                return "\"\"";
            }

            if (arg.Length == 0)
            {
                return "\"\"";
            }

            if (arg.IndexOfAny(new[] { ' ', '\t', '"', '\\' }) < 0)
            {
                return arg;
            }

            var builder = new StringBuilder();
            builder.Append('"');
            var backslashes = 0;

            foreach (var c in arg)
            {
                if (c == '\\')
                {
                    backslashes++;
                    continue;
                }

                if (c == '"')
                {
                    builder.Append('\\', backslashes * 2 + 1);
                    builder.Append('"');
                    backslashes = 0;
                    continue;
                }

                builder.Append('\\', backslashes);
                backslashes = 0;
                builder.Append(c);
            }

            builder.Append('\\', backslashes * 2);
            builder.Append('"');
            return builder.ToString();
        }
    }

    internal sealed class DeviceInfo
    {
        public string Serial { get; set; }
        public string State { get; set; }
        public string Details { get; set; }
        public string Source { get; set; }

        public override string ToString()
        {
            var suffix = string.IsNullOrWhiteSpace(Details) ? string.Empty : "  " + Details;
            var source = string.IsNullOrWhiteSpace(Source) ? string.Empty : Source + ": ";
            return source + Serial + "  [" + State + "]" + suffix;
        }
    }

    internal sealed class PackageInfo
    {
        public string Package { get; set; }
        public string Installer { get; set; }
        public string Uid { get; set; }
        public string Path { get; set; }
    }

    internal sealed class CommandResult
    {
        public int ExitCode { get; set; }
        public string Stdout { get; set; }
        public string Stderr { get; set; }

        public string Output
        {
            get
            {
                if (string.IsNullOrWhiteSpace(Stderr))
                {
                    return Stdout ?? string.Empty;
                }

                if (string.IsNullOrWhiteSpace(Stdout))
                {
                    return Stderr ?? string.Empty;
                }

                return Stdout + Stderr;
            }
        }
    }
}
