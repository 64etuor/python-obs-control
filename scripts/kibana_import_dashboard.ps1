param(
  [string]$KibanaUrl = "http://localhost:5601",
  [string]$NdjsonPath = "elk/kibana/lens_full.ndjson",
  [string]$DataViewsNdjsonPath = "elk/kibana/data_views.ndjson"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Push-Location $repoRoot

function Wait-KibanaReady {
  param([string]$Url, [int]$TimeoutSec = 90)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $base = $Url.TrimEnd('/')
      $r1 = Invoke-WebRequest -Uri "$base/api/status" -UseBasicParsing -TimeoutSec 5
      if ($r1.StatusCode -ge 200 -and $r1.StatusCode -lt 300) { return $true }
      Start-Sleep -Seconds 2
      $r2 = Invoke-WebRequest -Uri "$base/api/saved_objects/_find?type=dashboard&per_page=1" -UseBasicParsing -TimeoutSec 5 -Headers @{"kbn-xsrf" = "true"}
      if ($r2.StatusCode -ge 200 -and $r2.StatusCode -lt 300) { return $true }
    } catch {}
    Start-Sleep -Seconds 3
  }
  return $false
}

try {
  if (-not [System.IO.Path]::IsPathRooted($NdjsonPath)) { $NdjsonPath = Join-Path $repoRoot $NdjsonPath }
  if (-not [System.IO.Path]::IsPathRooted($DataViewsNdjsonPath)) { $DataViewsNdjsonPath = Join-Path $repoRoot $DataViewsNdjsonPath }
  if (-not (Test-Path $NdjsonPath -PathType Leaf)) { Write-Error "NDJSON not found: $NdjsonPath"; Pop-Location; exit 1 }
  if (-not (Test-Path $DataViewsNdjsonPath -PathType Leaf)) { Write-Error "NDJSON not found: $DataViewsNdjsonPath"; Pop-Location; exit 1 }

  Write-Host "Waiting for Kibana to be ready at $KibanaUrl ... (up to 5 minutes)"
  $ready = Wait-KibanaReady -Url $KibanaUrl -TimeoutSec 300
  if (-not $ready) {
    Write-Error "Kibana is not ready. Please ensure it is running at $KibanaUrl"
    Pop-Location
    exit 1
  }

  function Import-Ndjson([string]$FilePath) {
    Add-Type -AssemblyName System.Net.Http
    $handler = New-Object System.Net.Http.HttpClientHandler
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.DefaultRequestHeaders.Add("kbn-xsrf", "true")
    $client.DefaultRequestHeaders.Accept.Add([System.Net.Http.Headers.MediaTypeWithQualityHeaderValue]::new("application/json"))

    $endpoint = "$($KibanaUrl.TrimEnd('/'))/api/saved_objects/_import?overwrite=true"
    $uri = [System.Uri]::new($endpoint)
    $content = New-Object System.Net.Http.MultipartFormDataContent
    $stream = [System.IO.File]::OpenRead($FilePath)
    try {
      $fileContent = New-Object System.Net.Http.StreamContent($stream)
      $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/ndjson")
      $fileName = [System.IO.Path]::GetFileName($FilePath)
      $content.Add($fileContent, "file", $fileName)

      $response = $client.PostAsync($uri, $content).Result
      $status = [int]$response.StatusCode
      $body = $response.Content.ReadAsStringAsync().Result
      Write-Host "Import response status: $status"
      if ($body) { Write-Host $body }
      if (-not $response.IsSuccessStatusCode) { throw "Import failed with status $status" }
    } finally {
      if ($stream) { $stream.Dispose() }
      if ($content) { $content.Dispose() }
      if ($client) { $client.Dispose() }
    }
  }

  # Import order: Data Views first, then Lens/Dashboard
  Import-Ndjson -FilePath $DataViewsNdjsonPath
  Import-Ndjson -FilePath $NdjsonPath

  # Post-fix: Ensure Lens references ids are set (guards against undefined ids)
  try {
    $base = $KibanaUrl.TrimEnd('/')
    $hdr = @{"kbn-xsrf" = "true"}

    function Set-LensIndexPattern([string]$lensId, [string]$layerId, [string]$dataViewId) {
      $obj = Invoke-RestMethod -Uri "$base/api/saved_objects/lens/$lensId" -Headers $hdr -Method GET
      $attrs = $obj.attributes

      # Fix references ids
      $refs = @()
      foreach ($r in $obj.references) {
        if ($r.type -eq 'index-pattern') {
          $refs += @{ type='index-pattern'; name=$r.name; id=$dataViewId }
        } else {
          $refs += $r
        }
      }

      # Ensure current-indexpattern reference exists
      if (-not ($refs | Where-Object { $_.type -eq 'index-pattern' -and $_.name -eq 'indexpattern-datasource-current-indexpattern' })) {
        $refs += @{ type='index-pattern'; name='indexpattern-datasource-current-indexpattern'; id=$dataViewId }
      }

      $body = @{ attributes = $attrs; references = $refs } | ConvertTo-Json -Depth 100
      Invoke-RestMethod -Uri "$base/api/saved_objects/lens/$lensId" -Headers $hdr -Method PUT -ContentType 'application/json' -Body $body | Out-Null
    }

    # Apply to our lenses
    Set-LensIndexPattern -lensId 'logs_timeseries_count_lens' -layerId 'layer-logs-count' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'logs_top_loggers_lens' -layerId 'layer-logs-top' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'logs_top_hotkeys_func_lens' -layerId 'layer-logs-hotkeys' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'metrics_cpu_percent_lens' -layerId 'layer-metrics-cpu' -dataViewId 'metricbeat_metrics'
    Set-LensIndexPattern -lensId 'metrics_process_rss_lens' -layerId 'layer-metrics-rss' -dataViewId 'metricbeat_metrics'
    Set-LensIndexPattern -lensId 'logs_top_actions_lens' -layerId 'layer-logs-actions' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'logs_top_modules_lens' -layerId 'layer-logs-modules' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'metrics_process_cpu_lens' -layerId 'layer-metrics-proc-cpu' -dataViewId 'metricbeat_metrics'
    Set-LensIndexPattern -lensId 'metrics_process_vms_lens' -layerId 'layer-metrics-vms' -dataViewId 'metricbeat_metrics'
    Set-LensIndexPattern -lensId 'metrics_open_handles_lens' -layerId 'layer-metrics-handles' -dataViewId 'metricbeat_metrics'
    Set-LensIndexPattern -lensId 'logs_top_hotkey_combos_lens' -layerId 'layer-logs-hotkey-combos' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'logs_top_hotkey_targets_lens' -layerId 'layer-logs-hotkey-targets' -dataViewId 'python_obs_control_logs'
    Set-LensIndexPattern -lensId 'logs_hotkeys_timeseries_count_lens' -layerId 'layer-logs-hotkeys-count' -dataViewId 'python_obs_control_logs'
  } catch {
    Write-Warning "Lens post-fix failed: $($_.Exception.Message)"
  }
} catch {
  Write-Error "Import failed: $($_.Exception.Message)"
  Pop-Location
  exit 1
}

Pop-Location
