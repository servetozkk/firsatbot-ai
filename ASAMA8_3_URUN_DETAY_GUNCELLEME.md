# AŞAMA 8.3 – Ürün Detay Sayfası Güncellemesi

Bu sürümde ürün detay sayfasına şunlar eklendi:

- Ürün grubuna bağlı çalışan favori butonu
- Sayfa açıldığında favori durumunun `/favorites` üzerinden okunması
- Favoriye ekleme ve favoriden çıkarma işlemleri
- Aktif mağaza tekliflerinin kargo dahil toplam fiyata göre sıralanması
- Mevcut fiyat grafiği, teknik özellikler ve karşılaştırma alanlarının korunması

Çalıştırma:

```powershell
python -m uvicorn main:app --reload
```

Kontrol adresi:

```text
http://127.0.0.1:8000
```
