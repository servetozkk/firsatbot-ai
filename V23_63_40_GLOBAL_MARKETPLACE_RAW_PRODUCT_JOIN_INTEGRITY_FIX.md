# FirsatAI v23.63.40

## Global Marketplace Raw Product Join Integrity Fix

Scope is intentionally narrow.

The Global Marketplace product-detail serving query incorrectly joined
`global_offers.raw_product_id` against the legacy `products.id` namespace.
Those IDs are unrelated and may collide, causing a correct offer URL/price to
be displayed with another product's legacy title/image.

v23.63.40 changes offer display metadata to use the authoritative chain:

`global_offers.raw_product_id -> raw_products.id`

with an additional guard:

`raw_products.global_product_id == global_offers.global_product_id`

Title and image are now sourced from `raw_products.title_raw` and
`raw_products.image_raw`; if the guarded raw row is unavailable, the response
fails safely to the GlobalProduct canonical title/image.

Not changed:
- database contents or continuity
- ingestion/reconciliation
- canonical matcher
- price parsing/provenance
- GlobalOffer price/lifecycle behavior
- store adapters
- price-integrity/quarantine
- security challenge policy
- variant convergence (planned separately; no v23.63.40 mutation)
