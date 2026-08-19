# FırsatAI v21.0.0 - PRICE COMPARISON CORE

Bu sürüm FırsatAI'nin üretim okuma akışını Akakçe/Cimri tipi katalog-first fiyat karşılaştırma mimarisine taşır.

- GlobalProduct ana ürün kimliğidir.
- GlobalProductVariant varyant katmanıdır.
- GlobalOffer mağaza/satıcı teklifidir.
- GlobalOfferPriceHistory fiyat geçmişidir.
- Kullanıcı istekleri mağazaları canlı taramaz; global katalogdan hızlı cevap alır.
- Multi-store repair endpoint'i geliştirme/onarım aracı olarak korunur.
- Tekliflerde FRESH/STALE durumu `last_seen_at` üzerinden hesaplanır.
- En iyi fiyat hesabında varsa taze teklifler önceliklidir; taze teklif yoksa aktif stale teklifler fallback olur.
- v20.8 canonical identity ve v20.9 Hepsiburada session yönetimi korunur.

Yeni API'ler:

- GET `/api/price-comparison/v21/products/{global_product_id}`
- GET `/api/price-comparison/v21/search?q=...`
- GET `/api/runtime-identity/v210`

Referans ürün: Global Product 125.
