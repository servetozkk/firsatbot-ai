# FirsatAI v23.62.32

İdefix için açık zero-result kanıtı mevcutsa beklemeyi erken sonlandırır.

- V23.62.24 single strong-query politikası korunur.
- Erken çıkış yalnız `a[href*="/urun/"]` ürün linki yokken ve görünür body metninde açık ürün/sonuç bulunamadı işareti varken çalışır.
- Açık işaret yoksa mevcut tam browser arama yolu korunur.
- Identity, varyant/renk, detail, canonical ve price-integrity kuralları değiştirilmemiştir.
- Hepsiburada security challenge bypass edilmez.
