# FırsatAI v23.62.75 — Amazon Binding Real-Path Detail Cap

- v23.62.74 search optimizations preserved.
- Fixes the actual force/deep-refresh execution path in `BindingCrossStoreSearchService._scan_store`.
- Amazon candidate URLs are ordered/deduped, then capped to the strongest first candidate before `ScraperRegistry().scrape`.
- Expected runtime log: `V23.62.75 AMAZON BINDING REAL-PATH DETAIL CAP: detail_candidates=N -> 1` followed by `V20.4 scraper aktarımı [Amazon Türkiye]: 1 ...`.
- N11, identity gates, price-integrity quarantine, security fail-closed, store budget preserved.
