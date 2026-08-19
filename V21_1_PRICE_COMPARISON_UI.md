# FırsatAI v21.1.0 - Price Comparison UI

v21.0 katalog-first fiyat karşılaştırma çekirdeğinin kullanıcı arayüzü sürümüdür.

- `/fiyat-karsilastirma` katalog arama ekranı eklendi.
- `/fiyat-karsilastirma/urun/{global_product_id}` Akakçe/Cimri tipi mağaza teklif ekranı eklendi.
- Kullanıcı sayfaları canlı scraper çalıştırmaz; `GlobalProduct` ve `GlobalOffer` katalog verisini okur.
- En iyi fiyat, mağaza/satıcı, stok, FRESH/STALE güncellik, kargo ve mağazaya git bağlantısı gösterilir.
- `/api/price-comparison/v21/...` API sözleşmesi korunmuştur.
- Search API sonuçlarına `detail_url` eklendi.
- v20.8 canonical identity ve v20.9 Hepsiburada session katmanları değiştirilmedi.
