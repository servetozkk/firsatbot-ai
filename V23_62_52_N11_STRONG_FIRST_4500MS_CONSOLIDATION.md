# FirsatAI v23.62.52 — N11 Strong-First 4500ms Consolidation

This release simplifies the N11 first-query latency control without relaxing offer acceptance.

- Strong brand+model first navigation budget is consolidated to 4500 ms.
- The extra V23.62.51 450 ms near-miss probe is retired.
- Existing 350 ms same-DOM selector recovery remains after a timeout.
- Later N11 queries retain the existing full navigation budget.
- V23.62.50 verified search-card recovery remains preserved.
- Detail HTTP soft-cap remains 4.5 seconds.
- Security challenge bypass remains disabled.
- Price-integrity quarantine and production ingestion behavior are unchanged.
