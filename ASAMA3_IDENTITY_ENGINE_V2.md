# Aşama 3 — Identity Engine v2

Bu sürüm ürün varyantlarını doğru ayırır.

- Fold8 Ultra 256 GB ile Fold8 Ultra 1 TB farklı kimlik alır.
- Fold8 ile Fold8 Ultra farklı kimlik alır.
- Aynı kapasitedeki farklı renkler aynı karşılaştırma grubunda kalır.
- RAM bilgisi bulunduğunda kimliğe katılır.
- iPhone, Galaxy Fold/Flip/S/A/Z, Redmi Note, Redmi, Poco ve Xiaomi aileleri tanınır.

## Test

```powershell
python test_identity_engine_v2.py
```

Başarılı sonuç:

```text
IDENTITY ENGINE V2 TESTLERİ BAŞARILI
```

> Daha önce yanlış gruplandırılmış veriler otomatik silinmez. Test ortamında temiz
> başlangıç için eski SQLite veritabanının yedeğini alın ve kategori taramasını
> yeniden çalıştırın. Üretim verisi için silme yerine ayrıca güvenli taşıma
> (re-group migration) uygulanmalıdır.
