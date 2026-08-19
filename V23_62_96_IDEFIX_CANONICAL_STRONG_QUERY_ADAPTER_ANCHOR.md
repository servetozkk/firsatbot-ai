# FirsatAI v23.62.96

Idefix coverage correctness hotfix.

- Single bounded Idefix query now uses the canonical ingestion `search_query` first instead of a possibly brand-only synthesized query.
- Bounded navigation is 6.5s.
- Product readiness probe uses the same selector family as the Idefix adapter (`/urun/`, data-testid product anchors, data-product-url, product-class anchors).
- Anchor wait is bounded to at most 2.5s within the same store budget.
- Existing canonical identity, detail validation, color, security-challenge and price-integrity gates are unchanged.
- Amazon v23.62.91 and N11 v23.62.95 behavior are preserved.
