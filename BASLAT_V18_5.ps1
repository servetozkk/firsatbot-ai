$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "FirsatAI v18.5.0 baslatiliyor..."
Write-Host "Proje: $Root"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8:replace"
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Set-Location $Root
python -m uvicorn main:app --host 127.0.0.1 --port 8000
