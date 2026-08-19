# FırsatAI v22.8.0 — Amazon Exact-ASIN Price Recovery & Canonical Key Stabilization

Amazon fiyat sırası:
1. Mevcut detail DOM / JSON-LD
2. v22.7 embedded JSON/JS structured offer
3. v22.6 buying-options semantic fallback
4. v22.8 exact-ASIN Amazon search-result card fallback

v22.8 fallback güvenlik kuralları:
- Arama yalnız detail URL'den çıkarılan 10 karakterli ASIN ile yapılır.
- Yalnız `data-asin` veya `/dp/{ASIN}` bağlantısı TAM AYNI ASIN olan kart kabul edilir.
- Eski fiyat `.a-text-price` kullanılmaz.
- Exact-ASIN kart fiyatı tek başına Product oluşturmaz; detail HTML'den ad/marka/model yine doğrulanır.
- Sonraki v21.9 Price Integrity kapısı korunur.

Canonical key stabilizasyonu:
- Exact aynı `identity_source` aliasları merge edildikten sonra kazanan
  GlobalProduct.identity_key ve ProductGroup.group_key kesin olarak
  `sha256(identity_source)[:32]` değerine sabitlenir.
- Böylece aynı Redmi Watch'ın sonraki ingestion'da yeni global ID üretmesi engellenir.
- Farklı identity_source için key çakışması görülürse otomatik merge yapılmaz.

Runtime:
- GET /api/runtime-identity/v228
