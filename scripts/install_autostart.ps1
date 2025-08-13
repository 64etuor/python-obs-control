Param(
  [string]$TaskName = "PythonObsControl-Autostart",
  [int]$Port = 8080,
  [bool]$EnableElk = $true,
  [bool]$Reload = $false
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  return (Split-Path -Parent $scriptDir)
}

$repoRoot = Resolve-RepoRoot
$runScript = Join-Path $repoRoot "run_server.ps1"
if (!(Test-Path $runScript -PathType Leaf)) { throw "run_server.ps1 not found: $runScript" }

$psArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runScript`" -Port $Port -Reload:`$$Reload"
if (-not $EnableElk) { $psArgs += " -NoElk" }

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType InteractiveToken

try {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
} catch {}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Autostart python-obs-control on user logon" | Out-Null
Write-Host "Registered logon autostart task '$TaskName' (Port=$Port, EnableElk=$EnableElk, Reload=$Reload)." -ForegroundColor Green


