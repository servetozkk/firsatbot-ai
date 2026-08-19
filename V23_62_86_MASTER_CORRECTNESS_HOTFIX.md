# FirsatAI v23.62.86 MASTER correctness hotfix

- Force deep-refresh response now uses the actual v23.62.86 single runtime constant.
- Smoke test AST-inspects the real force endpoint body so stale-version leaks cannot pass by matching unrelated endpoints.
- Amazon phone detail preflight distinguishes Pro+ / Pro Plus from plain Pro before browser scraping.
- Up to 8 already-ranked Amazon candidates may be checked by cheap fail-closed title preflight; browser scraping still begins only on the first variant-compatible candidate.
- Security challenge bypass remains disabled.
- Price-integrity quarantine and v23.62.85 WAL-safe continuity are preserved.
