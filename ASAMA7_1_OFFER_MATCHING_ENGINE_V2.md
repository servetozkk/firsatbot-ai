# Aşama 7.1 — Offer Matching Engine V2

Bu sürüm, farklı mağazalarda farklı biçimde yazılan aynı ürünleri güvenli şekilde ortak ürün grubuna bağlar.

## Eşleşme kuralları

- Marka kesin eşleşir.
- Model ailesi benzerlik puanıyla karşılaştırılır.
- RAM ve depolama çelişirse eşleşme reddedilir.
- Pro, Max, Ultra, FE gibi varyantlar çelişirse eşleşme reddedilir.
- Renk grup kimliğine dahil edilmez.
- Birden fazla adayın skoru birbirine çok yakınsa otomatik birleştirme yapılmaz.

## Test

```powershell
python test_offer_matching_engine_v2.py
```
