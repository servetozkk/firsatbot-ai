# v3.1.4 — Akıllı Görsel Filtreleme Motoru

- Logo, ikon, rozet, banner, kampanya, kargo, ödeme, TR GO, placeholder ve takip pikselleri galeriden elenir.
- URL'de açık boyutu 260×260 altı olan görseller alınmaz.
- Sayfadaki bütün URL'leri taramak yerine ürün galerisi düğümleri ve güvenilir JSON image/gallery alanları kullanılır.
- Aynı görselin thumb/original varyantları tek kayda düşürülür ve en kaliteli sürüm tercih edilir.
- `python -m app.backfill_product_images --clean-only --limit 500` mevcut galerileri internete çıkmadan temizler.
- `python -m app.backfill_product_images --force --limit 500` ürün sayfalarını yeniden tarayıp galerileri kaliteli görsellerle yeniler.
- Backfill komutu migration'ı kendisi çalıştırdığı için `image_gallery` sütunu eksik hatası vermez.
