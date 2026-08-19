param(
    [string]$SourceProject = "$env:USERPROFILE\Downloads\firsatbot-v3-1-4-akilli-gorsel-filtreleme-motoru\firsatbot-akakce-mantigi-asama8-1"
)

$ErrorActionPreference = "Stop"
$CurrentProject = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceData = Join-Path $SourceProject "data"
$TargetData = Join-Path $CurrentProject "data"

if (-not (Test-Path $SourceData)) {
    Write-Host "Kaynak data klasoru bulunamadi:" -ForegroundColor Red
    Write-Host $SourceData
    Write-Host "Komutu kaynak proje yolunu vererek calistirabilirsin:"
    Write-Host '.\restore_clean_gallery_data.ps1 -SourceProject "C:\...\eski-proje"'
    exit 1
}

New-Item -ItemType Directory -Force -Path $TargetData | Out-Null
Copy-Item (Join-Path $SourceData "*") $TargetData -Recurse -Force
Write-Host "Onceki calisan veritabani ve temiz galeri verileri kopyalandi." -ForegroundColor Green

Set-Location $CurrentProject
python -m app.backfill_product_images --clean-only --limit 500
Write-Host "Galeri tekrar filtrelendi. Simdi sunucuyu baslatabilirsin." -ForegroundColor Green
