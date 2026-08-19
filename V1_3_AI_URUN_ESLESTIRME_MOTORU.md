# v1.3 – AI Ürün Eşleştirme Motoru

Bu sürüm, farklı mağazalarda farklı yazılan aynı ürünleri daha güvenli biçimde tek ürün grubuna bağlar.

## Eşleştirme sinyalleri

- Marka ve kategori
- Ürün ailesi / model adı benzerliği
- Pro, Ultra, Max, FE gibi varyantlar
- RAM ve depolama kapasitesi
- Model ve ürün kodu
- Ekran boyutu ve şebeke tipi
- Renk farkını teknik grubu bölmeden açıklama

## Güvenlik kuralları

- RAM, depolama, kategori, marka veya varyant çelişiyorsa otomatik birleştirme yapılmaz.
- En iyi iki adayın puanı birbirine yakınsa sonuç belirsiz kabul edilir.
- Otomatik eşleştirme eşiği 88, yüksek güven eşiği 95 puandır.

## Denetim raporu

Veritabanını değiştirmeden mevcut ürünleri kontrol etmek için:

```powershell
python -m app.audit_ai_product_matching --limit 1000
```

Sonuç `ai_product_matching_report.json` dosyasına yazılır.
