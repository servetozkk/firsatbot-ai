# FırsatAI v23.0.0 — Canonical Lifecycle Single Source of Truth

Amaç: aynı canonical `identity_source` için ProductGroup ve ACTIVE GlobalProduct ID'lerinin kalıcı olarak sabit kalması.

## Tek resolver
- ProductGroup create/get: `canonical_lifecycle_v230_service.resolve_product_group`
- GlobalProduct create/get: `canonical_lifecycle_v230_service.resolve_global_product`
- Her ikisi de önce exact `identity_source`, sonra canonical key ile lookup yapar.

## DB-level koruma
Startup audit sonrası SQLite unique partial indexleri kurulur:
- `ux_v230_product_groups_identity_source`
- `ux_v230_global_products_active_identity_source`

Böylece concurrency veya eski bir kod yolu ikinci canonical kayıt oluşturmaya çalışsa bile DB engeller.

## API
- GET `/api/runtime-identity/v230`
- GET `/api/canonical-lifecycle/v230/status`
- GET `/api/canonical-lifecycle/v230/status?identity_source=identity_v3:...`
- POST `/api/canonical-lifecycle/v230/audit`

Amazon v22.9 `NO_BUYABLE_OFFER`, v22.6 GlobalOffer reliability, v22.5 wearable identity, v22.3 phone identity ve v21.9 Price Integrity korunur.
