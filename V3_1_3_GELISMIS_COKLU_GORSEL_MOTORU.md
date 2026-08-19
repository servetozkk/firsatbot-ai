# v3.1.3 Gelişmiş Çoklu Görsel Motoru

- Ürün modellerine `image_gallery` alanı eklendi.
- Trendyol, Hepsiburada, Amazon, Teknosa ve generic scraper HTML içindeki tüm ürün görsellerini toplar.
- JSON-LD, gömülü JavaScript, `srcset`, zoom görselleri ve CDN URL'leri taranır.
- Tekrarlanan görseller normalize edilerek elenir.
- Galeri en fazla 60 farklı görsel gösterebilir.
- Tam ekran galeride zoom, fare tekerleği, çift tıklama, klavye ve mobil kaydırma vardır.
- Eski ürünleri zenginleştirmek için: `python -m app.backfill_product_images --limit 500`
