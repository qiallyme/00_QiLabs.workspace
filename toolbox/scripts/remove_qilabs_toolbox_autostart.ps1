$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "QiLabs Toolbox.lnk"
if (Test-Path $shortcutPath) {
  Remove-Item $shortcutPath -Force
  Write-Host "Removed autostart shortcut:" $shortcutPath
} else {
  Write-Host "No QiLabs Toolbox autostart shortcut found."
}
