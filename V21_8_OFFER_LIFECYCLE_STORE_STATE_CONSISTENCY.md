# FırsatAI v21.8.0 – Offer Lifecycle & Store State Consistency

- Crawler/backoff durumu ile GlobalOffer lifecycle durumu ayrıldı.
- Başarısız refresh, tarama öncesinde aktif olan doğrulanmış teklifleri pasifleştiremez.
- Legacy ProductOffer + RawProduct bağı mevcutsa eksik GlobalOffer güvenli biçimde yeniden kurulabilir.
- Yeni sürüm başlatıcısı önceki FırsatAI sürümlerindeki daha zengin canlı SQLite DB'yi otomatik devralır ve mevcut DB'yi önce yedekler.
- tracked_store_count, searchable_store_count ve active_offer_store_count ayrı raporlanır.
- Kaynak mağaza crawler backoff listesine dahil edilmez.
- v20.8 canonical identity ve strict teknik kapılar korunur.
