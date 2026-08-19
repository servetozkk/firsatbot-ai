# FirsatAI v23.11.0 — Detail-Stage Canonical Matcher Bridge

## Amaç
v23.10 search-card discovery gerçek cross-store adaylarını buluyordu; ancak detail scraper sonrası V23.4 canonical bridge bazı kategorileri legacy V17 notebook model-family parserına düşürüp yeniden RED ediyordu.

## Düzeltmeler
- Lenovo laptop: exact MTM/SKU (örn. 82XB009GTX) + storage/RAM discriminator.
- MacBook Neo/Air/Pro: natural family + storage; renk identity gate değildir.
- Tablet: canonical family + storage, RAM yalnız iki tarafta da açık olduğunda ek discriminator.
- Audio/headphone: canonical family + accessory/kılıf guard.
- Tablet dispatch phone matcher'dan önce çalışır; Galaxy Tab artık telefon olarak route edilmez.

## Korunan sözleşmeler
- v23.10 search-card canonical family bridge
- v22.5 wearable family/variant guard
- v23.3 phone base/5G + Pro/Pro+ guards
- v23.6 original-vs-compatible accessory guard
- v23.9 multi-category price routing
- v23.8 production stress endpoint

Runtime: `GET /api/runtime-identity/v2311`
Stress: `POST /api/production-stress/v238/runs`
