# FırsatAI v12.1.0 — Production Operations

- `/health/live` canlılık endpoint'i eklendi.
- `/health/ready` SQLite bütünlüğü ve production güvenlik gereksinimlerini denetler.
- Güçlü `SECRET_KEY` ve `ADMIN_ACCESS_TOKEN` üreten production `.env` aracı eklendi.
- SQLite online backup API kullanan tutarlı yedek aracı eklendi.
- Identity Engine, Global Catalog, Offers ve matching davranışı değiştirilmedi.
