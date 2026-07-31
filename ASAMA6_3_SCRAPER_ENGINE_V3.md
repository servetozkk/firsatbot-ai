# Aşama 6.3 — Scraper Engine V3

## Hepsiburada liste modu

Hepsiburada kategori taraması artık ürün detay sayfalarını açmaz. Kategori kartından:

- ürün adı
- güncel fiyat
- eski fiyat
- ürün URL'si
- ürün görseli
- ürün kodu

alınır ve doğrudan mevcut Identity Engine + Offer Engine akışına kaydedilir.

Hepsiburada kartında ad veya fiyat alınamayan kayıtlar detay sayfasına gönderilmez. Böylece güvenlik doğrulamasında uzun süre bekleme ve tekrar deneme döngüsü oluşmaz.

Trendyol ve Teknosa için mevcut detay kuyruğu davranışı korunmuştur.

## Test

```powershell
python test_scraper_engine_v3.py
```

Beklenen son satır:

```text
SCRAPER ENGINE V3 TESTLERİ BAŞARILI
```
