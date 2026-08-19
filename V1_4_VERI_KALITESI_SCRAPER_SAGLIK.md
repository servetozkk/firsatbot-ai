# v1.4 Veri Kalitesi ve Scraper Sağlık Merkezi

- `/admin/data-quality` yönetim ekranı eklendi.
- Ürünlere 100 üzerinden veri kalite puanı verilir.
- Eksik görsel, marka, model, kategori, teknik özellik ve fiyat geçmişi raporlanır.
- Mağaza teklif sayıları ve kategori tarama geçmişinden scraper sağlık oranı gösterilir.
- Olası aynı mağaza / aynı grup tekrarları izlenir.
- JSON raporu üretmek için: `python -m app.generate_data_quality_report`
