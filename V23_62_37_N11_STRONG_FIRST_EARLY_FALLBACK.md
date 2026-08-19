# V23.62.37 — N11 Strong-First Early Fallback

- Strong canonical brand+model first query keeps v23.62.33 order.
- Strong-first navigation trigger reduced from 6500 ms to 3250 ms.
- If it times out, the existing second query starts immediately.
- Weak/model-first queries keep 4500 ms; subsequent queries keep full budget.
- Sync Playwright browser/page is not shared across threads; no unsafe parallel browser access was added.
- v23.62.35 scope hotfix and v23.62.36 İdefix bounded no-candidate logic are preserved.
- Identity, accessory, color, detail, canonical and price-integrity gates are unchanged.
