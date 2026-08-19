# FirsatAI v23.62.57

Observation-only timing correctness release.

- Separates N11 Chromium launch + new_page startup from unattributed search time.
- Preserves v23.62.56 N11 behavior and all security/price-integrity gates.
- Removes UTF-8 BOM from launcher BAT to avoid the stray @echo startup error.
