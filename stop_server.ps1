Param(
  [int]$Port = 8080
)

$cons = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if (-not $cons) { Write-Host "이미 꺼져 있음"; exit 0 }

$pids = $cons | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $pids) {
  try {
    Stop-Process -Id $procId -Force -ErrorAction Stop
    Write-Host "종료: PID $procId"
  } catch {
    Write-Warning "종료 실패: PID $procId ($($_.Exception.Message))"
  }
}


