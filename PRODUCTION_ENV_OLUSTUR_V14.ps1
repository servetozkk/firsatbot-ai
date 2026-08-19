$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Out = Join-Path $Root '.env.production'

if (Test-Path $Out) {
    throw '.env.production zaten mevcut. Guvenlik icin uzerine yazilmadi.'
}

function New-Hex([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        if ($null -ne $rng) { $rng.Dispose() }
    }
    return ([System.BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

function Normalize-Host([string]$Value) {
    $hostValue = ''
    if ($null -ne $Value) { $hostValue = $Value.Trim() }
    $hostValue = $hostValue -replace '^https?://', ''
    $hostValue = $hostValue.TrimEnd('/')

    # IPv6 haric normal host:port girislerinde portu kaldir.
    if ($hostValue -notmatch '^\[' -and $hostValue -match '^(.*?):\d+$') {
        $hostValue = $Matches[1]
    }
    return $hostValue
}

$domainInput = Read-Host 'Alan adini yazin (ornek: firsatai.com; yerel test: 127.0.0.1)'
$domain = Normalize-Host $domainInput
if ([string]::IsNullOrWhiteSpace($domain)) {
    throw 'Alan adi bos olamaz.'
}

$secret = New-Hex 48
$token = New-Hex 32

if ($domain -eq '127.0.0.1' -or $domain -eq 'localhost') {
    $trustedHosts = '127.0.0.1,localhost'
    Write-Host 'BILGI: Yerel test hostu kullaniliyor. Canli yayin oncesi gercek alan adiyla yeniden olusturun.' -ForegroundColor Yellow
}
else {
    $trustedHosts = "$domain,www.$domain"
}

$content = @"
APP_NAME=FirsatAI
APP_VERSION=14.0.0
APP_ENV=production
APP_HOST=127.0.0.1
APP_PORT=8000
ENABLE_SCHEDULER=1
SECRET_KEY=$secret
ADMIN_ACCESS_TOKEN=$token
SECURE_COOKIES=1
CSRF_ENABLED=1
RATE_LIMIT_ENABLED=1
TRUSTED_HOSTS=$trustedHosts
DATABASE_PATH=data/products.db
"@

# Windows PowerShell 5.1 dahil tum surumlerde UTF-8 BOM olmadan yaz.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Out, $content, $utf8NoBom)

Write-Host "OK  $Out olusturuldu." -ForegroundColor Green
Write-Host 'UYARI: Bu dosyayi paylasmayin ve Git deposuna eklemeyin.' -ForegroundColor Yellow
