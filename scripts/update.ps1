Param(
  [string]$Repo    = "C:\git_projects\python-obs-control",
  [string]$Venv    = "C:\git_projects\python-obs-control\.venv",
  [string]$Branch  = "main",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $Repo)) { throw "Repo not found: $Repo" }
if (!(Test-Path $Venv)) { throw "Venv not found: $Venv (먼저 venv 만들고 requirements 설치 필요)" }

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
  
  # Use safer pull instead of reset --hard
  if ($Force) {
    Write-Host "Force mode: Discarding local changes..." -ForegroundColor Yellow
    git reset --hard "origin/$Branch"
  } else {
    git pull origin $Branch
  }
  
  & "$Venv\Scripts\python.exe" -m pip install -r "$Repo\requirements.txt"
  Write-Host "Update done."
} else {
  Write-Host "Already up-to-date: $local"
}


