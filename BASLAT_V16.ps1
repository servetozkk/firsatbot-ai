$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:FIRSATAI_NONINTERACTIVE = "1"

$Connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach($Connection in $Connections){
    $ProcessId = $Connection.OwningProcess
    if($ProcessId -and $ProcessId -ne $PID){
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1

Write-Host "FirsatAI v16.0.1 baslatiliyor..."
Write-Host "Proje: $Root"
python -X utf8 -m uvicorn main:app --host 127.0.0.1 --port 8000
