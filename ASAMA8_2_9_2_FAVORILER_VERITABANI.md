# Aşama 8.2.9.2 — Favoriler Veritabanı

Bu aşamada yalnızca favoriler veritabanı altyapısı tamamlandı.

## Eklenenler

- `Favorite` SQLAlchemy modeli
- `favorites` tablosu
- Ziyaretçi + ürün grubu benzersizlik kuralı
- Ürün grubuna foreign key
- İzole SQLite testi

## Test

```powershell
python test_favorites_database.py
```

Beklenen çıktı:

```text
FAVORITES DATABASE TEST PASSED
```
