# FırsatAI v23.8.0 — 10 Product Multi-Category Production Stress

Bu sürüm matcher veya serving davranışını değiştirmez.
Amaç, v23.7 üretim ingestion zincirini tam 10 benzersiz gerçek ürünle ölçmektir.

API
- GET  /api/runtime-identity/v238
- GET  /api/production-stress/v238/runtime
- POST /api/production-stress/v238/runs
- GET  /api/production-stress/v238/runs/{stress_run_id}
- GET  /api/production-stress/v238/runs

POST body:
{
  "urls": [
    "https://...",
    "... toplam tam 10 benzersiz URL ..."
  ]
}

Stress raporu:
- product_count / completed / failed / success rate
- unique GlobalProduct count
- duplicate input / duplicate ingestion
- newly saved offer count
- final served offer count
- quarantine count
- average served store count
- category distribution
- price-integrity product-kind distribution
- canonical single_source_of_truth
- duplicate group/global counts
- identity contract violations
- final price-audit errors
- zero-serving products
- per-product final serving snapshot

Operational stress score:
- ingestion success: 35
- canonical integrity: 25
- at least one served offer per completed product: 20
- unique canonical identity: 10
- final price audit health: 10

Readiness:
- READY >= 90 (ve failure=0, single_source=true, audit_error=0)
- WATCH >= 75
- NOT_READY < 75

Önerilen 10 ürün dağılımı:
- 3 telefon (base / Pro / 5G varyantlarını içerebilir)
- 2 laptop
- 1 akıllı saat
- 1 kulaklık
- 1 orijinal aksesuar
- 1 tablet
- 1 farklı elektronik kategori

V23.7 fiyat lifecycle, v23.6 originality guard, v23.5 FK-safe cleanup ve
v23.4 canonical matcher bridge korunmuştur.
