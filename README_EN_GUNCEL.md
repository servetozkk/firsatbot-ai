# FırsatBot AI — EN GÜNCEL

Bu klasör, 26 Temmuz 2026 tarihinde temizlenmiş proje sürümüdür.

## Çalıştırma

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
uvicorn main:app --reload
```

Tarayıcı: `http://127.0.0.1:8000`

## Yapılan temizlik

- Türkçe karakter bozulmaları UTF-8 olarak düzeltildi.
- `.bak`, `backup`, debug HTML ve eski kod dökümleri kaldırıldı.
- Kaynak dosyalardaki UTF-8 BOM işaretleri temizlendi.
- Python dosyaları sözdizimi kontrolünden geçirildi.

Orijinal GitHub sürümünüzü silmeden önce bu klasörü ayrı bir yerde test edin.


## v21.9.0 Price Integrity & Quarantine Engine
Şüpheli fiyatlar GlobalOffer içinde korunur ancak kullanıcıya sunulan aktif teklif/best-price havuzundan çıkarılır. Teknosa laptop parserında düşük yan sayı fiyat seçimine karşı baskın sayfa fiyatı kontrolü eklenmiştir.
