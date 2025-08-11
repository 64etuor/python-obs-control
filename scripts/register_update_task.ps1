Param(
  [string]$Repo = "C:\git_projects\python-obs-control",
  [string]$Venv = "C:\git_projects\python-obs-control\.venv",
  [string]$Time = "04:30"
)

$ErrorActionPreference = "Stop"

$script = Join-Path $Repo "scripts\update.ps1"
if (!(Test-Path $script)) { throw "update.ps1 not found: $script" }

$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Repo `"$Repo`" -Venv `"$Venv`""
$at = [DateTime]::ParseExact($Time, "HH:mm", $null)
$trigger = New-ScheduledTaskTrigger -Daily -At $at

Register-ScheduledTask -TaskName "obs-control-auto-update" -Action $action -Trigger $trigger -Description "Auto update python-obs-control (daily)" -User $env:USERNAME -RunLevel Highest -Force
Write-Host "Registered task 'obs-control-auto-update' daily at $Time."


