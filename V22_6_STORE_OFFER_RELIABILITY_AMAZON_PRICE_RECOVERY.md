# FırsatAI v22.6.0 — Store Offer Reliability & Amazon Price Recovery

- Amazon ürün sayfasında klasik Buy Box fiyatı yoksa "buying options / yeni teklifler"
  bağlamından semantik fiyat kurtarma yapılır.
- Taksit, aylık kredi, kupon, kazanç/tasarruf tutarları satış fiyatı sayılmaz.
- GlobalOffer kullanıcıya servis edilen tek teklif kaynağı olarak açıkça denetlenir.
- Her mağaza için en fazla bir aktif GlobalOffer bırakılır.
- Farklı mağazaların teklifleri birbirini arşivleyemez.
- Legacy ProductOffer sayacı yalnız eski karşılaştırma katmanıdır; mağaza kapsamı
  ölçümünde GlobalOffer active_store_count kullanılır.
- Hepsiburada güvenlik challenge davranışı korunur; bypass uygulanmaz.

API:
- GET /api/runtime-identity/v226
- GET /api/store-offer-reliability/v226/products/{global_product_id}
- POST /api/store-offer-reliability/v226/products/{global_product_id}/audit
