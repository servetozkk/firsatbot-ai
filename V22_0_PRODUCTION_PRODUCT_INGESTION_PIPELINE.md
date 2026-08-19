# FırsatAI v22.0.0 — Production Product Ingestion Pipeline

Yeni ürün ekleme akışı tek üretim zincirinde birleştirildi:

1. Kaynak ürün URL doğrulama ve scrape
2. Canonical identity
3. Legacy + RawProduct + GlobalProduct/Variant/GlobalOffer upsert
4. Kaynak teklif için v21.9 fiyat bütünlüğü
5. v21.8 smart store refresh/backoff
6. v20.8+ strict identity/technical matching
7. GlobalOffer senkronizasyonu
8. Son fiyat bütünlüğü audit
9. READY

Admin > Ürün Ekle ekranı artık bu pipeline'ı kullanır.
Kaynak save sırasında legacy V14.9 otomatik repair kapatılır; böylece aynı ürün için iki ayrı mağaza taraması başlamaz.

API:
- POST /api/product-ingestion/v220/products
- GET /api/product-ingestion/v220/tasks/{task_id}
- GET /api/product-ingestion/v220/runtime
- GET /api/runtime-identity/v220
