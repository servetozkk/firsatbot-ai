# FirsatAI v23.62.67 - Production Stability Baseline Lock

Bu sürüm scraping davranışını değiştirmez. v23.62.66 davranışı production baseline olarak dondurulmuştur.

## Kanıtlanan baseline
- 15/15 soak PASS
- Contract violation: 0
- Offer count: 6/6 sabit
- Store success count: 6/6 sabit
- N11: 15/15 SUCCESS (%100)
- N11 ortalama: 6.745 sn (min 5.967, max 8.796)
- Total ortalama: 12.533 sn (min 11.093, max 13.321)

## Regression lock
Kritik scraping/recovery dosyalarının SHA-256 fingerprintleri `V23_62_67_BASELINE_FINGERPRINTS.json` içinde tutulur. Smoke testi bu fingerprintleri doğrular.

## Korunan kontratlar
- N11 USER_INGESTION force inclusion
- ProductOffer store/SKU conflict-safe convergence
- ProductOffer URL unique convergence
- N11 recent verified detail bridge ve cold-start persisted trust
- N11 process-wide detail HTTP session
- 4500 ms strong-first search budget
- 350 ms selector recovery
- 4.5 sn detail HTTP timeout
- Security challenge bypass disabled
- Price integrity quarantine preserved
