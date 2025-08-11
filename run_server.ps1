Param(
  [int]$Port = 8080,
  [string]$Bind = "0.0.0.0"
)

$env:PYTHONPATH = "$PSScriptRoot"

# 1) On launch, attempt a one-shot update (git pull + pip install)
try {
  $repo = "$PSScriptRoot"
  $venv = Join-Path $PSScriptRoot ".venv"
  $updateScript = Join-Path $PSScriptRoot "scripts/update.ps1"
  if ((Test-Path $updateScript -PathType Leaf) -and (Test-Path $venv)) {
    Write-Host "[run_server] Running one-shot update..." -ForegroundColor Cyan
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File "$updateScript" -Repo "$repo" -Venv "$venv" 2>&1
    $out | ForEach-Object { Write-Host $_ }
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

# 3) Start server with auto-reload
uvicorn app.presentation.app_factory:app --host $Bind --port $Port --reload

