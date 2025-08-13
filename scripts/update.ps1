Param(
  [string]$Repo    = "C:\git_projects\python-obs-control",
  [string]$Venv    = "C:\git_projects\python-obs-control\.venv",
  [string]$Branch  = "main",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

function Find-RepoRoot([string]$startDir) {
  try {
    $dir = (Resolve-Path $startDir).Path
  } catch { return $null }
  while ($true) {
    if (Test-Path (Join-Path $dir ".git")) { return $dir }
    $parent = Split-Path -Parent $dir
    if (-not $parent -or $parent -eq $dir) { break }
    $dir = $parent
  }
  return $null
}

# Auto-detect repo path if not provided or invalid
if (-not $Repo -or -not (Test-Path $Repo)) {
  $autoRepo = Find-RepoRoot $PSScriptRoot
  if ($autoRepo) {
    $Repo = $autoRepo
    Write-Host "Repo auto-detected: $Repo" -ForegroundColor Cyan
  }
}

if (!(Test-Path $Repo)) { throw "Repo not found: $Repo" }

# Resolve/Create venv if missing
if (-not $Venv -or -not (Test-Path $Venv)) {
  $Venv = Join-Path $Repo ".venv"
}
$pyexe = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $pyexe)) {
  Write-Host "Virtualenv not found, creating: $Venv" -ForegroundColor Yellow
  try { New-Item -ItemType Directory -Force -Path $Venv | Out-Null } catch {}
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    & py -3 -m venv "$Venv"
  } else {
    & python -m venv "$Venv"
  }
  if (-not (Test-Path $pyexe)) { throw "Failed to create virtualenv at $Venv" }
  try { & $pyexe -m pip install --upgrade pip setuptools wheel | Out-Null } catch {}
}

Set-Location $Repo

git remote update | Out-Null
$local  = (git rev-parse HEAD).Trim()
$remote = (git rev-parse "origin/$Branch").Trim()

if ($Force -or $local -ne $remote) {
  Write-Host "Updating to origin/$Branch ..."
  
  # Check for uncommitted changes first
  $status = git status --porcelain
  if ($status -and -not $Force) {
    Write-Host "Error: You have uncommitted changes. Commit them first or use -Force to override." -ForegroundColor Red
    Write-Host "Uncommitted changes:" -ForegroundColor Yellow
    git status --short
    exit 1
  }
  
  if ($Force) {
    Write-Host "Force mode: Discarding local changes..." -ForegroundColor Yellow
    git reset --hard "origin/$Branch"
  } else {
    git pull origin $Branch
  }
  
  if (Test-Path (Join-Path $Repo "requirements.txt")) {
    & "$pyexe" -m pip install -r (Join-Path $Repo "requirements.txt")
  } else {
    Write-Host "requirements.txt not found, skipping install." -ForegroundColor Yellow
  }
  Write-Host "Update done."
} else {
  Write-Host "Already up-to-date: $local"
}


