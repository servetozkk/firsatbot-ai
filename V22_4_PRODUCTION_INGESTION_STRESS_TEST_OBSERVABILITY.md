# FırsatAI v22.4.0 — Production Ingestion Stress Test & Observability

v22.0–v22.3 üretim ingestion zincirini değiştirmeden gözlemlenebilir hale getirir.

Kalıcı metrikler (`data/ingestion_observability_v224.json`, son 500 ingestion):
- toplam / source / discovery / price-integrity süreleri
- taranan ve skip edilen mağaza sayıları
- mağaza başarı ve başarısızlık sayıları
- yeni kaydedilen offer sayısı
- aktif offer sayısı
- quarantine sayısı
- canonical ProductGroup / GlobalProduct duplicate kontrolü
- hata türleri
- kategori dağılımı

Kontrollü stress testi aynı anda birden fazla tam ingestion zinciri açmaz. En fazla 10 URL kabul eder ve ürünleri sırayla işler.

API:
- GET `/api/runtime-identity/v224`
- GET `/api/ingestion-observability/v224/summary`
- GET `/api/ingestion-observability/v224/tasks?limit=50`
- GET `/api/ingestion-observability/v224/products/{global_product_id}`
- POST `/api/ingestion-observability/v224/stress/run`
- GET `/api/ingestion-observability/v224/stress/{run_id}`

Stress POST body örneği:
```json
{
  "urls": [
    "https://.../urun-1",
    "https://.../urun-2"
  ]
}
```
