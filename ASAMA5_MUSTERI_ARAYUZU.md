# Aşama 5.1 — Müşteri Ana Sayfası ve Canlı Arama

Bu sürüm ana sayfayı Offer Engine V2 verilerine bağlar.

## Eklenenler

- Ana sayfadaki ürün kartları artık `ProductGroup + ProductOffer + Store` tablolarından üretilir.
- Aynı ürünün mağaza teklifleri tek kartta değerlendirilir.
- Karttan doğrudan ürün karşılaştırma detayına gidilir.
- En ucuz fiyat, en yüksek mağaza fiyatı ve tasarruf oranı hesaplanır.
- Arama kutusuna iki karakter yazıldığında canlı ürün önerileri açılır.
- Öneride ürün resmi, marka, kategori, mağaza ve güncel en düşük fiyat gösterilir.

## Test

```powershell
python test_public_catalog_v1.py
uvicorn main:app --reload
```

Tarayıcı:

- Ana sayfa: http://127.0.0.1:8000/
- Ürün listesi: http://127.0.0.1:8000/karsilastir
- Arama API örneği: http://127.0.0.1:8000/api/search/suggestions?q=iphone
