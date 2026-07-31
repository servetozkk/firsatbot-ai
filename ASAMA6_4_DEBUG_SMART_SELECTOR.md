# Aşama 6.4 — Debug ve Akıllı Selector

Bu sürüm Hepsiburada kategori taramasında üç katman kullanır:

1. Geniş DOM kart seçicileri
2. JSON-LD / Next.js / Redux gömülü veri yedeği
3. Kart bulunamazsa otomatik HTML, ekran görüntüsü ve metadata kaydı

Debug dosyaları `debug/hepsiburada/<tarih>_sayfa_<no>/` altında oluşur.
`SCRAPER_DEBUG=false` ile kapatılabilir.

Admin kategori aktif/pasif işleminde eski veya silinmiş kimlik gelirse ham 404 yerine
panelde anlaşılır hata mesajına yönlendirilir.
