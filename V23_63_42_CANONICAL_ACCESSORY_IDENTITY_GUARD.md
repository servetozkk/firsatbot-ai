# FirsatAI v23.63.42 — Canonical Accessory Identity Guard

Scope is intentionally narrow and fail-closed.

- Explicit accessory merchant/raw brand is authoritative over compatibility targets such as MacBook/iPhone/Galaxy.
- Compatibility wording (uyumlu, kilif, kapak, canta, stand, tutucu, koruyucu) cannot promote an accessory brand to Apple/Samsung/Xiaomi.
- Accessory identities do not inherit target-device RAM, storage or screen-size capabilities.
- Startup convergence repairs only ACTIVE GlobalProducts whose current canonical brand is a known compatibility target and whose MATCHED raw rows unanimously resolve to one corrected brand/family/identity.
- GlobalProduct/ProductGroup collisions or raw disagreement abort that repair row (fail closed).
- GlobalOffer, variants, prices, price history, alerts, store scrapers and v23.63.40/v23.63.41 behavior are preserved.
- Source/title corruption (e.g. GP43) and test/demo catalog rows are explicitly out of scope for this release.
