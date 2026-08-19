# FırsatAI v23.3.0 — Cross-Store Identity Normalization & Strict Variant Matcher

Bu sürüm v23.2 bulk testinde görülen false-negative eşleştirmeleri düzeltir.

Telefon discovery:
- Redmi 15C / Redmi Note 15 Pro / POCO / Galaxy / Xiaomi aileleri query parser tarafından telefon olarak tanınır.
- RAM telefon discovery zorunlu kapısı değildir.
- Depolama normalize edilir: `8+256`, `8/256`, `256 GB 8 GB RAM` -> storage=256.
- `Redmi 15C` != `Redmi 15C 5G`.
- `Redmi Note 15 Pro` != `Redmi Note 15 Pro+`.
- Açık 5G yalnız name/model seviyesinde canonical discriminator olur; specs içindeki 5G canonical key'i bölmez.

Aksesuar:
- Manufacturer part code exact-match yolu eklendi.
- `MD3J4TU/A`, `MD3J4TUA`, `MD3J4TU-A` aynı canonical kod kabul edilir.
- `MUVV3TU/A` farklı kod olduğu için kesin reddedilir.
- Cep Telefonu Aksesuar kategorisi telefon matcher'a düşmez.

Korunan katmanlar:
- v23.2 bulk orchestrator
- v23.1 canonical lifecycle / wearable contract
- laptop strict matcher
- Amazon NO_BUYABLE_OFFER
- GlobalOffer reliability
- Price Integrity

Runtime:
- GET /api/runtime-identity/v233
