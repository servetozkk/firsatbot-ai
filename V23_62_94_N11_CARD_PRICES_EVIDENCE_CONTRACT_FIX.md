# FirsatAI v23.62.94

N11 v23.62.93 rendered recovery evidence-contract hotfix.

- Search service stores DOM card prices in `card_prices`.
- v23.62.93 recovery incorrectly read only `price_values`/`prices`, so it returned before browser preflight.
- v23.62.94 reads `card_prices` first and keeps the same score316 + family + variant + storage + exact-color rendered gate.
- Security challenge bypass remains disabled.
- Normal attach and price-integrity pipeline remain unchanged.
