# FırsatAI v22.7.0 — Amazon Structured Offer & Canonical Alias Reliability

Amazon:
- application/json, data-a-state ve embedded JS state içindeki offer fiyatları taranır.
- priceToPay / buyingPrice / offerPrice / currentPrice / buybox / buyingOptions güçlü pozitif kanıttır.
- installment / monthly / financing / coupon / savings / listPrice / oldPrice negatif kanıttır.
- TRY/TL para birimi kanıtı tercih edilir.
- Structured extraction başarısızsa v22.6 DOM/buying-options fallback korunur.

Canonical alias reliability:
- Yalnız TAM AYNI identity_source kayıtları merge edilir.
- Aynı fiziksel ürünün geçmiş hash/key farkı nedeniyle tekrar GlobalProduct oluşturması önlenir.
- ProductGroup aliasları da aynı exact identity_source kuralıyla birleştirilir.
- GlobalProduct.active_offer_count gerçek ACTIVE GlobalOffer sayısından yeniden hesaplanır.
- Farklı identity_source kayıtları hiçbir koşulda bu audit tarafından birleştirilmez.

API:
- GET /api/runtime-identity/v227
- GET /api/canonical-alias/v227/status
- POST /api/canonical-alias/v227/audit
- GET /api/store-offer-reliability/v226/products/{global_product_id}
