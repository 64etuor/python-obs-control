param(
  [string]$ComposeFile = "elk/docker-compose.yml"
)

# Ensure script runs from repo root (parent of scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Push-Location $repoRoot

Write-Host "Starting ELK stack using" $ComposeFile "from" (Get-Location) "..."

# Ensure Docker is available
$dockerVersion = docker version 2>$null
if (-not $?) {
  Write-Error "Docker is not available. Please install Docker Desktop and ensure it is running."
  Pop-Location
  exit 1
}

# Compose up
docker compose -f $ComposeFile up -d
$status = $?
Pop-Location
if (-not $status) { exit 1 }

Write-Host "Elasticsearch: http://localhost:9200"
Write-Host "Kibana:        http://localhost:5601"
Write-Host "Logs index:    python-obs-control-<env>-YYYY.MM.DD"
