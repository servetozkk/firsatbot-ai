# v1.2 – Akıllı Veri Motoru

Bu sürüm ürün adı, model, açıklama ve ham özelliklerden otomatik teknik veri çıkarır.

## Çıkarılan temel alanlar

- RAM ve depolama
- İşlemci ve ekran kartı
- Ekran boyutu, panel, çözünürlük ve yenileme hızı
- Kamera, batarya ve hızlı şarj
- 5G, eSIM, NFC, Wi‑Fi ve Bluetooth
- Renk

## Çalışma şekli

Yeni teklifler kaydedilirken otomatik çıkarımlar önce `title-parser-v1` kaynağıyla yazılır.
Scraper'dan gerçek teknik özellik gelirse sonradan yazıldığı için otomatik çıkarımın üzerine geçer.

Mevcut verileri güncellemek için:

```powershell
python -m app.backfill_inferred_product_features
```

Bu işlem ürünleri veya teklifleri silmez; yalnızca eksik teknik özellik tablosunu zenginleştirir.
