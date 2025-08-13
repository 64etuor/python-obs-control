Param(
  [int]$Port = 8080,
  [string]$Bind = "0.0.0.0",
  [switch]$NoElk,
  [bool]$Reload = $true
)

$env:PYTHONPATH = "$PSScriptRoot"

# If local virtualenv exists, prepend its Scripts to PATH so 'uvicorn' resolves
try {
  $venvScripts = Join-Path $PSScriptRoot ".venv"
  $venvScripts = Join-Path $venvScripts "Scripts"
  if (Test-Path $venvScripts) {
    $env:PATH = "$venvScripts;$env:PATH"
  }
} catch {}

# 1) On launch, attempt a one-shot update (git pull + pip install)
$updateAttempted = $false
$updateOk = $true
try {
  $repo = "$PSScriptRoot"
  $venv = Join-Path $PSScriptRoot ".venv"
  $updateScript = Join-Path $PSScriptRoot "scripts/update.ps1"
  if ((Test-Path $updateScript -PathType Leaf) -and (Test-Path $venv)) {
    Write-Host "[run_server] Running one-shot update..." -ForegroundColor Cyan
    $updateAttempted = $true
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File "$updateScript" -Repo "$repo" -Venv "$venv" 2>&1
    $out | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
      $updateOk = $false
      Write-Host "[run_server] Update returned non-zero exit code ($LASTEXITCODE). Will run with current code as-is." -ForegroundColor Yellow
    }
  } else {
    Write-Host "[run_server] Skip update (missing venv or update script)." -ForegroundColor Yellow
  }
} catch { Write-Host "[run_server] update failed: $($_.Exception.Message)" -ForegroundColor Red }

# 2) Load .env and override environment (ensure .env wins over machine/user env)
try {
  $dotenv = Join-Path $PSScriptRoot ".env"
  if (Test-Path $dotenv -PathType Leaf) {
    Get-Content $dotenv | ForEach-Object {
      $line = $_.Trim()
      if (-not $line -or $line.StartsWith("#")) { return }
      $idx = $line.IndexOf('=')
      if ($idx -lt 1) { return }
      $k = $line.Substring(0, $idx).Trim()
      $v = $line.Substring($idx + 1).Trim()
      # strip quotes if present
      if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
        $v = $v.Substring(1, $v.Length-2)
      }
      if ($k) { Set-Item -Path Env:$k -Value $v }
    }
    Write-Host "[run_server] .env applied to process environment (override)" -ForegroundColor Cyan
  }
} catch { Write-Host "[run_server] .env load failed: $($_.Exception.Message)" -ForegroundColor Yellow }

# 3) Optionally start ELK stack tied to server lifecycle
$elkStarted = $false
$enableElk = -not $NoElk
try {
  if ($enableElk) {
    $elkUpScript = Join-Path $PSScriptRoot "scripts/elk_up.ps1"
    $elkCompose = Join-Path $PSScriptRoot "elk/docker-compose.yml"
    if ((Test-Path $elkUpScript -PathType Leaf) -and (Test-Path $elkCompose -PathType Leaf)) {
      try {
        Write-Host "[run_server] Starting ELK (docker compose up -d)" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$elkUpScript" 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -eq 0) {
          $elkStarted = $true
        } else {
          Write-Host "[run_server] ELK up returned non-zero exit code ($LASTEXITCODE). Continuing without ELK." -ForegroundColor Yellow
        }
      } catch {
        Write-Host "[run_server] ELK up failed: $($_.Exception.Message). Continuing without ELK." -ForegroundColor Yellow
      }
    } else {
      Write-Host "[run_server] Skipping ELK (scripts/compose not found)." -ForegroundColor Yellow
    }
  } else {
    Write-Host "[run_server] ELK disabled via -NoElk switch." -ForegroundColor Yellow
  }

  # 4) Start server (reload optional) with fallback to python -m uvicorn
  function Invoke-Uvicorn([string]$uvHost, [int]$uvPort, [bool]$uvReload) {
    $uvArgs = @("app.presentation.app_factory:app", "--host", $uvHost, "--port", $uvPort)
    if ($uvReload) { $uvArgs += "--reload" }
    $started = $false
    try {
      Write-Host "[run_server] Starting via 'uvicorn'..." -ForegroundColor Cyan
      uvicorn @uvArgs
      $started = $true
    } catch {
      if ($_.Exception -and ($_.Exception.GetType().Name -like "*CommandNotFound*")) {
        Write-Host "[run_server] 'uvicorn' not found, retrying with 'python -m uvicorn'..." -ForegroundColor Yellow
      } else {
        Write-Host "[run_server] uvicorn start raised: $($_.Exception.Message). Retrying with 'python -m uvicorn'..." -ForegroundColor Yellow
      }
    }
    if (-not $started) {
      try {
        python -m uvicorn @uvArgs
        $started = $true
      } catch {
        Write-Host "[run_server] python -m uvicorn failed: $($_.Exception.Message)" -ForegroundColor Red
        throw
      }
    }
  }

  if (-not $updateOk -and $updateAttempted) {
    Write-Host "[run_server] Proceeding without update (using current working copy)." -ForegroundColor Yellow
  }

  Invoke-Uvicorn -uvHost $Bind -uvPort $Port -uvReload:$Reload
}
finally {
  if ($elkStarted) {
    $elkDownScript = Join-Path $PSScriptRoot "scripts/elk_down.ps1"
    if (Test-Path $elkDownScript -PathType Leaf) {
      try {
        Write-Host "[run_server] Stopping ELK (docker compose down)" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$elkDownScript" 2>&1 | ForEach-Object { Write-Host $_ }
      } catch {
        Write-Host "[run_server] ELK down failed: $($_.Exception.Message)" -ForegroundColor Yellow
      }
    }
  }
}

