param(
  [string]$ComposeFile = "elk/docker-compose.yml"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Push-Location $repoRoot

Write-Host "Stopping ELK stack using" $ComposeFile "from" (Get-Location) "..."

docker compose -f $ComposeFile down

Pop-Location
