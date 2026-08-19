$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Write-Host "FirsatAI v19.4.0 baslatiliyor..."
Write-Host "Proje: $Root"
$Connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach($Connection in $Connections){
    if($Connection.OwningProcess -and $Connection.OwningProcess -ne $PID){
        Stop-Process -Id $Connection.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
python -m uvicorn main:app --host 127.0.0.1 --port 8000
