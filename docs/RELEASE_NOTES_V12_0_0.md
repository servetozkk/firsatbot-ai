# FırsatAI v12.0.0 — Production Final

FırsatAI'nin Akakçe mantığındaki çok mağazalı fiyat karşılaştırma çekirdeği final sürüme taşındı.

- Global ürün kataloğu ve global varyantlar
- Çok mağazalı teklifler ve fiyat sıralaması
- 4G/5G, RAM/VRAM, SSD/NVMe varyant güvenliği
- Katalog temizliği ve güvenli Cross-Store onarımları
- Kanonik `/urun/{identity_key}` ürün bağlantısı
- Production Core sağlık denetimi
- 100.000 satırlık sentetik ölçek testi
- SQLite bütünlük, foreign key ve performans indeks kontrolleri

Canlı sunucuda `APP_ENV=production`, güçlü `SECRET_KEY`, `ADMIN_ACCESS_TOKEN`, `SECURE_COOKIES=1` ve gerçek `TRUSTED_HOSTS` yapılandırılmalıdır.
