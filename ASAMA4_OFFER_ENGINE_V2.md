# Aşama 4 — Offer Engine V2

Bu aşamada mevcut Identity Engine V2'nin ürettiği ortak kimlikler mağaza teklifleriyle birleştirilir.

## Davranış

- Aynı kimliğe sahip Teknosa ve Trendyol kayıtları tek `product_group` altında tutulur.
- Her mağaza URL'si ayrı `product_offer` olur.
- Satın alınabilir en düşük toplam fiyat `is_best_offer` olarak işaretlenir.
- Bir mağaza ürününün fiyatı değişirse yeni teklif oluşturulmaz; mevcut teklif güncellenir ve `offer_price_history` kaydı eklenir.
- Kargo fiyatı varsa karşılaştırmaya ürün fiyatıyla birlikte dahil edilir.

## Test

```powershell
python test_offer_engine_v2.py
```

Beklenen son satır:

```text
OFFER ENGINE V2 TESTLERİ BAŞARILI
```

## Eski kayıtları yeniden bağlama

Önce `data/products.db` dosyasının yedeğini alın. Ardından:

```powershell
python backfill_offer_engine_v2.py
```
