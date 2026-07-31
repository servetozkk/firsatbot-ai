# Aşama 6.1 — Hepsiburada Kategori Entegrasyonu

Bu sürümde Hepsiburada kategori bağlantıları kategori paneline bağlandı.

## Eklenenler

- `HepsiburadaCategoryScraper`
- `CategoryScraperRegistry` mağaza kaydı
- `sayfa` parametresi ile sayfalama
- Görünür bağlantı + gömülü JSON/script bağlantı çıkarımı
- Güvenlik doğrulaması algılama ve anlaşılır uyarı
- Sistem Chrome'u yoksa Playwright Chromium geri dönüşü
- Çevrimdışı entegrasyon testi

## Test

```powershell
python test_hepsiburada_category_v1.py
```

Beklenen son satır:

```text
HEPSİBURADA CATEGORY V1 TESTLERİ BAŞARILI
```

## İsteğe bağlı canlı test

```powershell
$env:HEPSIBURADA_CATEGORY_URL="https://www.hepsiburada.com/cep-telefonlari-c-371965"
python test_hepsiburada_category_v1.py
```

Ardından uygulamayı açıp `/admin/categories` ekranından Hepsiburada kategori URL'si eklenebilir.
