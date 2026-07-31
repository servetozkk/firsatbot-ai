# Aşama 2 — Kategori Yönetim Paneli

Çalıştırma:

```powershell
cd C:\Users\Tekno\Downloads\firsatbot-akakce-mantigi-asama2\firsatbot-akakce-mantigi-asama2
uvicorn main:app --reload
```

Panel:

```text
http://127.0.0.1:8000/admin/categories
```

İlk testte ürün limitini 5 yapın. Kategori ekledikten sonra `Tara` düğmesine basın.
Tarama arka planda çalışır; durum ve sonuç panelde otomatik güncellenir.
