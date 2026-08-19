# FırsatAI v23.2.0 — Bulk Catalog Ingestion Orchestrator

Amaç:
- Tek tek ürün ekleme yerine 1 batch içinde en fazla 100 benzersiz ürün URL'si işlemek.
- Ürünleri sırayla çalıştırmak; aynı anda birden fazla tam scraper zinciri açmamak.
- Her ürün mevcut production ingestion pipeline'ını aynen kullanır.
- Bir ürünün hatası diğer ürünleri durdurmaz.
- Input içindeki tekrar URL'ler çalıştırılmadan elenir.
- Batch sonucu restart sonrası `data/bulk_ingestion_v232.json` içinde tutulur.
- Son 100 batch saklanır.
- Batch sonunda v23.1 canonical lifecycle kontrol edilir.

API:
- GET  /api/runtime-identity/v232
- GET  /api/bulk-ingestion/v232/runtime
- POST /api/bulk-ingestion/v232/runs
- GET  /api/bulk-ingestion/v232/runs
- GET  /api/bulk-ingestion/v232/runs/{run_id}

POST body:
{
  "urls": [
    "https://...",
    "https://..."
  ]
}

İzlenen batch metrikleri:
- processed_count
- completed_count
- failed_count
- success_rate_percent
- newly_saved_offer_count
- duplicate_ingestion_count
- unique_global_product_count
- global_product_ids
- canonical_lifecycle.single_source_of_truth
