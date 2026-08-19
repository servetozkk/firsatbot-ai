# FirsatAI v23.10.0 — Cross-Store Matcher Canonical Family Bridge

Amaç: v23.9 canonical identity/price routing ile cross-store search-card gate arasında ortak family dili kurmak.

## Düzeltmeler
- Lenovo 82XB009GTX gibi rakamla başlayan exact MTM/SKU kodları discovery aşamasında tanınır.
- MacBook Neo doğal canonical family olarak tanınır.
- Apple Watch SE 3 / Ultra nesil kimliği cross-store kartlarında tanınır.
- Redmi Buds 6 Play audio family gate ile tanınır; kılıf/koruma kabı RED kalır.
- Galaxy Tab A11 tablet family gate ile tanınır; yanlış depolama RED kalır.
- v23.3 phone network/varyant, v23.6 aftermarket accessory ve eski strict laptop korumaları korunur.
- v23.8 production stress motoru ve v23.9 price-kind routing değiştirilmez.

Runtime: `GET /api/runtime-identity/v2310`
Stress: `POST /api/production-stress/v238/runs`
