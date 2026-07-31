# Aşama 1 — Otomatik Kategori Tarama Sistemi

Bu paket mevcut projeyi silmeden genişletir.

## Desteklenen mağazalar
- Trendyol
- Teknosa

## Çalıştırma
```powershell
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

## Hızlı test
```powershell
python test_category_pipeline.py
```

## Kullanım
Yönetim panelinden veya `/api/categories` uç noktasından Teknosa/Trendyol
kategori URL'si ekleyin. Scheduler aktif kategorileri mevcut 15 dakikalık
periyotla tarar.

Sistem:
1. Kategori sayfalarını gezer.
2. Benzersiz ürün URL'lerini toplar.
3. Mevcut mağaza ürün scraper'ına gönderir.
4. Ürünleri veritabanına ve takip listesine kaydeder.
5. Var olan ürünlerde mevcut `save_product` davranışını korur.
