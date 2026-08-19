# FırsatAI v21.4.0 - Store Coverage Engine

Bu sürüm v21.3 Catalog Feed Engine üzerine mağaza aday kapsamasını geliştirir.

- N11, Amazon Türkiye, MediaMarkt, Vatan ve İdefix için canonical kısa sorgu önce denenir.
- Vatan path araması `+` yerine percent-encoding kullanır.
- Her mağazadan tek aday yerine en güçlü en fazla 3 aday detay scraper/strict matcher katmanına geçebilir.
- Nihai `validate_variant`, CPU/RAM/SSD/varyant güvenlik kapıları korunur.
- Pazarama ve İdefix için StoreAdapter kayıtları eklendi.
- Hepsiburada SECURITY_CHALLENGE davranışı değiştirilmedi.
- Global Product / ProductGroup / canonical identity çekirdeği değiştirilmedi.
