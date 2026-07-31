# Aşama 6.2 — Scraper Engine V2

Bu sürüm kategori taramasını iki aşamaya ayırır:

1. Kategori/listeden ürün URL'lerini hızlı toplama
2. Ürün detaylarını sınırlı worker havuzunda paralel tarama

Veritabanı ve `products.json` yazımları ana thread üzerinde seri yapılır. Bu,
SQLite kilitlenme riskini azaltır. Hepsiburada tarayıcısı varsayılan olarak
headless çalışır ve her worker ayrı Chrome profil klasörü kullanır.

## Ayarlar

`.env.scraper.example` içindeki değerler ortam değişkeni olarak ayarlanabilir:

- `SCRAPER_HEADLESS=true`
- `SCRAPER_WORKERS=3`
- `SCRAPER_REQUEST_DELAY=0.6`
- `SCRAPER_RETRY_COUNT=1`

PowerShell örneği:

```powershell
$env:SCRAPER_HEADLESS="true"
$env:SCRAPER_WORKERS="3"
$env:SCRAPER_REQUEST_DELAY="0.8"
uvicorn main:app --reload
```

Güvenlik doğrulamasını görmek gerektiğinde yalnızca geçici olarak:

```powershell
$env:SCRAPER_HEADLESS="false"
```
