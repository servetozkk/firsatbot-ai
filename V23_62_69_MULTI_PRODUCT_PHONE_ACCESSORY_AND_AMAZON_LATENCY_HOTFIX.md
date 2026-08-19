# FirsatAI v23.62.69

Multi-product regression hotfix based on production coverage findings.

- Product 137 Redmi Watch 5 Active: Amazon browser fallback was observed at 78.358s with NO_BUYABLE_OFFER. Requests-first and exact-ASIN recovery are preserved; BrowserEngine fallback is bounded to 15s navigation, 1s initial wait, no scroll.
- Product 143 Redmi Note 15 Pro: N11 search admitted a phone screen-protector card (nano cam / jelatin / seramik film) at score 280. Phone search-card accessory hard-reject vocabulary now includes jelatin, nano cam, seramik film, koruyucu film, temperli cam, tempered glass.
- v23.62.68 force store budget=11 and minimum-success contract are preserved.
- Security challenge bypass remains disabled; price integrity quarantine remains preserved.
