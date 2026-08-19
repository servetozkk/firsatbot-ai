$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Db=Join-Path $Root 'data\products.db'
if(!(Test-Path $Db)){ throw "Veritabanı bulunamadı: $Db" }
$Dest=Join-Path $Root 'data\backups\production_v14'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$Stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$Out=Join-Path $Dest "products_v14_$Stamp.db"
$Py=(Get-Command python -ErrorAction SilentlyContinue).Source
if(!$Py){$Py=(Get-Command py -ErrorAction Stop).Source}
& $Py -c "import sqlite3; s=sqlite3.connect(r'$Db'); d=sqlite3.connect(r'$Out'); s.backup(d); d.close(); s.close(); print('OK  SQLite tutarlı yedek oluşturuldu')"
if($LASTEXITCODE-ne 0){throw 'SQLite yedekleme başarısız.'}
Write-Host "YEDEK: $Out" -ForegroundColor Green
