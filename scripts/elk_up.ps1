param(
  [string]$ComposeFile = "elk/docker-compose.yml",
  [int]$DockerStartupTimeoutSec = 120
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Push-Location $repoRoot

Write-Host "Starting ELK stack using" $ComposeFile "from" (Get-Location) "..."

function Test-DockerAvailable {
  docker version > $null 2>&1
  return ($LASTEXITCODE -eq 0)
}

function Get-DockerDesktopPath {
  $candidates = @()
  if ($Env:ProgramFiles) {
    $candidates += (Join-Path $Env:ProgramFiles "Docker/Docker/Docker Desktop.exe")
  }
  if (${Env:ProgramFiles(x86)}) {
    $candidates += (Join-Path ${Env:ProgramFiles(x86)} "Docker/Docker/Docker Desktop.exe")
  }
  if ($Env:LocalAppData) {
    $candidates += (Join-Path $Env:LocalAppData "Docker/Docker/Docker Desktop.exe")
  }
  foreach ($p in $candidates) {
    if (Test-Path $p -PathType Leaf) { return $p }
  }
  return $null
}

function Test-DockerEnginePipe {
  try { return (Test-Path "\\.\pipe\docker_engine") } catch { return $false }
}


if (-not (Test-DockerAvailable)) {
  Write-Host "Docker is not available. Launching Docker Desktop UI..." -ForegroundColor Yellow

  $desktopExe = Get-DockerDesktopPath
  if ($desktopExe) {
    try { Start-Process -FilePath $desktopExe | Out-Null } catch { }
  } else {
    Write-Error "Docker Desktop executable not found. Please install Docker Desktop."
    Pop-Location
    exit 1
  }

  $deadline = (Get-Date).AddSeconds($DockerStartupTimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-DockerAvailable -or Test-DockerEnginePipe) { break }
    Start-Sleep -Seconds 1
  }

  if (-not (Test-DockerAvailable -or Test-DockerEnginePipe)) {
    Write-Error "Docker engine did not become ready within $DockerStartupTimeoutSec seconds."
    Pop-Location
    exit 1
  }
}

docker compose -f $ComposeFile up -d
$status = $?
Pop-Location
if (-not $status) { exit 1 }

Write-Host "Elasticsearch: http://localhost:9200"
Write-Host "Kibana:        http://localhost:5601"
Write-Host "Logs index:    python-obs-control-<env>-YYYY.MM.DD"
