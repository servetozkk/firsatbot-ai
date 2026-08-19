# FırsatAI v22.9.0

Amazon Buyable Offer Resolution + Canonical Lookup-Before-Create

- Detail sayfasında hedef ASIN fiyatı varsa mevcut parser kullanılır.
- Fiyat yoksa detail HTML içindeki TAM AYNI ASIN `/gp/offer-listing/{ASIN}` bağlantısı takip edilir.
- Offer-listing içinde yalnız gerçek teklif fiyat selectorları kullanılır.
- Sponsorlu/recommended ürün `priceAmount` değerleri kullanılmaz.
- Offer-listing ve exact-ASIN fallback de fiyat üretmezse, gerçek detail kanıtı varsa `NO_BUYABLE_OFFER` döner.
- ProductGroup ve GlobalProduct create edilmeden önce exact `identity_source` aranır.
- Exact canonical source bulunduğunda mevcut kayıt yeniden kullanılır; yeni ID oluşturulmaz.
- Laptop/telefon/wearable strict identity ve Price Integrity korunur.
