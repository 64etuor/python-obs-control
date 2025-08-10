Param(
  [int]$Port = 8080,
  [string]$Bind = "0.0.0.0"
)

$env:PYTHONPATH = "$PSScriptRoot"

uvicorn app.presentation.app_factory:app --host $Bind --port $Port --reload

