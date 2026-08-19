# FırsatAI v21.3.0 - Catalog Feed Engine

Bu sürüm mevcut ürün detay tasarımını değiştirmez. V21.2 katalog-first ürün detay ekranını arka planda besleyen kontrollü teklif besleme motorunu ekler.

## Temel davranış

- Kullanıcı ürün sayfasını açtığında canlı mağaza taraması yapılmaz.
- Arka plan motoru aktif GlobalProduct kayıtlarından katalog kapsamı zayıf veya fiyatları eski olanları önceliklendirir.
- Mevcut v14 multi-store repair, v20.8 canonical identity ve strict matcher zinciri yeniden kullanılır; eşleştirme mantığı kopyalanmaz.
- Her ürün ayrı hata sınırındadır. Bir ürünün veya Hepsiburada gibi tek mağazanın başarısız olması diğer katalog ürünlerinin beslenmesini durdurmaz.
- GlobalOffer kayıtları mevcut sync/pipeline üzerinden güncellenir; yeni paralel katalog modeli oluşturulmaz.

## Varsayılan çalışma sınırları

- `CATALOG_FEED_ENABLED=1`
- `CATALOG_FEED_INTERVAL_MINUTES=30`
- `CATALOG_FEED_BATCH_SIZE=3`
- `CATALOG_FEED_STALE_HOURS=6`
- `CATALOG_FEED_INITIAL_DELAY_SECONDS=90`

Bu değerler ortam değişkenleriyle değiştirilebilir.

## API

- `GET /api/catalog-feed/v213/status`
- `POST /api/catalog-feed/v213/run?limit=3&stale_hours=6&candidate_limit=50&parallel_workers=3`
- `POST /api/catalog-feed/v213/products/125/refresh?candidate_limit=50&parallel_workers=3`
- `GET /api/runtime-identity/v213`

## Korunan çekirdek

- v20.8 canonical identity
- Store SKU Parser v2
- RAM/SSD izolasyonu
- strict technical conflict rejection
- ProductGroup/global product tekilleştirme
- v20.9 Hepsiburada challenge/session davranışı
- v21.2 mevcut ürün detay Price Comparison Core entegrasyonu
