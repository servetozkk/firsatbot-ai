# FırsatAI v23.5.0 — FK-Safe Canonical Cleanup

v23.4 gerçek bulk testinde eşleştirme başarıyla düzeldi; ancak N11 aday akışında
eski GlobalProduct `id=74` silinirken SQLite `FOREIGN KEY constraint failed`
hatası görüldü.

Kök neden:
- Eski cleanup yalnız RawProduct ve GlobalOffer bağlılığını kontrol ediyordu.
- GlobalOfferPriceHistory / GlobalPriceAlert ve variant çocuk FK'ları hesaba katılmıyordu.

v23.5:
- Cleanup öncesi session flush edilir.
- Taşınmış GlobalOffer'a ait price history canonical hedefe relink edilir.
- GlobalPriceAlert canonical hedefe taşınır; aynı visitor/target alarmı varsa duplicate merge edilir.
- RawProduct, GlobalOffer, price history, alert ve variant-child referansları tekrar sayılır.
- Herhangi bir referans kalıyorsa eski GlobalProduct silinmez; `ARCHIVED` bırakılır.
- Ancak bütün doğrudan ve variant referansları sıfırsa variantlar ve GlobalProduct silinir.
- Cleanup sonucu offer attach sonucuna `cleanup` alanıyla eklenir.

Korunan davranış:
- v23.4 canonical matcher bridge
- Redmi 15C base / 5G ayrımı
- Redmi Note 15 Pro / Pro+ ayrımı
- Telefon query'de RAM/SSD yok
- Apple manufacturer part-code exact match
- Amazon NO_BUYABLE_OFFER
- Price Integrity
- Bulk ingestion
