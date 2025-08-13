Param(
  [int]$Port = 8080,
  [bool]$EnableElk = $true
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot { (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) }
$repoRoot = Resolve-RepoRoot
$runScript = Join-Path $repoRoot "run_server.ps1"
$stopScript = Join-Path $repoRoot "stop_server.ps1"

if (!(Test-Path $stopScript -PathType Leaf)) {
  @'
Param([int]$Port = 8080)
$cons = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if (-not $cons) { Write-Host "이미 꺼져 있음"; exit 0 }
($cons | Select-Object -ExpandProperty OwningProcess -Unique) | ForEach-Object {
  try { Stop-Process -Id $_ -Force -ErrorAction Stop; Write-Host "종료: PID $_" } catch { Write-Warning "종료 실패: PID $_ ($($_.Exception.Message))" }
}
'@ | Out-File -FilePath $stopScript -Encoding utf8 -Force
}

$W = New-Object -ComObject WScript.Shell
function Make($name, $psArgs, $icon){
  $s = $W.CreateShortcut("$env:USERPROFILE\Desktop\$name.lnk")
  $s.TargetPath = "powershell.exe"
  $s.Arguments  = "-NoProfile -ExecutionPolicy Bypass -Command $psArgs"
  $s.WorkingDirectory = $repoRoot
  if(Test-Path $icon){ $s.IconLocation = "$icon,0" }
  $s.Save()
}

$eye = Join-Path $repoRoot "assets\icons\eye.svg"
$eyeOff = Join-Path $repoRoot "assets\icons\eye-off.svg"
$startArgs = "& `"$runScript`" -Port $Port" + ($(if($EnableElk){''}else{' -NoElk'}))

Make "서버 켜기" $startArgs $eye
Make "서버 끄기" "& `"$stopScript`" -Port $Port" $eyeOff

Write-Host "바탕화면 바로가기 생성 완료" -ForegroundColor Green


