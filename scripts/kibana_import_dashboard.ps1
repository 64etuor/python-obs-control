param(
  [string]$KibanaUrl = "http://localhost:5601",
  [string]$NdjsonPath = "elk/kibana/dashboard.ndjson"
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
  if (-not [System.IO.Path]::IsPathRooted($NdjsonPath)) {
    $NdjsonPath = Join-Path $repoRoot $NdjsonPath
  }
  if (-not (Test-Path $NdjsonPath -PathType Leaf)) {
    Write-Error "NDJSON not found: $NdjsonPath"
    Pop-Location
    exit 1
  }

  Write-Host "Waiting for Kibana to be ready at $KibanaUrl ... (up to 5 minutes)"
  $ready = Wait-KibanaReady -Url $KibanaUrl -TimeoutSec 300
  if (-not $ready) {
    Write-Error "Kibana is not ready. Please ensure it is running at $KibanaUrl"
    Pop-Location
    exit 1
  }

  Add-Type -AssemblyName System.Net.Http
  $handler = New-Object System.Net.Http.HttpClientHandler
  $client = New-Object System.Net.Http.HttpClient($handler)
  $client.DefaultRequestHeaders.Add("kbn-xsrf", "true")
  $client.DefaultRequestHeaders.Accept.Add([System.Net.Http.Headers.MediaTypeWithQualityHeaderValue]::new("application/json"))

  $endpoint = "$($KibanaUrl.TrimEnd('/'))/api/saved_objects/_import?overwrite=true"
  $uri = [System.Uri]::new($endpoint)
  $content = New-Object System.Net.Http.MultipartFormDataContent
  $stream = [System.IO.File]::OpenRead($NdjsonPath)
  try {
    $fileContent = New-Object System.Net.Http.StreamContent($stream)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/ndjson")
    $fileName = [System.IO.Path]::GetFileName($NdjsonPath)
    $content.Add($fileContent, "file", $fileName)

    $response = $client.PostAsync($uri, $content).Result
    $status = [int]$response.StatusCode
    $body = $response.Content.ReadAsStringAsync().Result
    Write-Host "Import response status: $status"
    if ($body) { Write-Host $body }
    if (-not $response.IsSuccessStatusCode) {
      throw "Import failed with status $status"
    }
  } finally {
    if ($stream) { $stream.Dispose() }
    if ($content) { $content.Dispose() }
    if ($client) { $client.Dispose() }
  }
} catch {
  Write-Error "Import failed: $($_.Exception.Message)"
  Pop-Location
  exit 1
}

Pop-Location
