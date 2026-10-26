$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Execute install-windows.ps1 primeiro." }
if (-not (Test-Path ".env")) { throw "Arquivo .env ausente." }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
$Log = Join-Path $Root "logs\server.log"
& (Join-Path $Root ".venv\Scripts\python.exe") -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1 --log-level info *>> $Log
