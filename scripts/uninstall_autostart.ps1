Param(
  [string]$TaskName = "PythonObsControl-Autostart"
)

$ErrorActionPreference = "Stop"

try {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop | Out-Null
  Write-Host "Removed logon autostart task '$TaskName'." -ForegroundColor Green
} catch {
  Write-Warning "Autostart task '$TaskName' not found or removal failed: $($_.Exception.Message)"
}


