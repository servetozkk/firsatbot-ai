# FırsatAI v21.9.0 — Price Integrity & Quarantine Engine

Bu sürüm yanlış parse edilmiş fiyatların kullanıcıya en iyi teklif olarak sunulmasını engeller.

- GlobalOffer silinmez; güçlü emsal kanıtıyla anomali tespit edilirse `QUARANTINED` olur.
- Karantinalı teklif `best_price`, aktif teklif listesi ve AI satın alma karar havuzuna girmez.
- Yeni scraper sonucu aşırı sapmalıysa mevcut doğrulanmış GlobalOffer fiyatı korunabilir.
- Açılışta mevcut katalog denetlenir; örneğin 21.999 / 24.863 TL seviyesindeki emsaller yanında 1.500 TL teklif karantinaya alınır.
- Canonical identity, strict matcher, v21.7 backoff ve v21.8 data continuity korunur.
