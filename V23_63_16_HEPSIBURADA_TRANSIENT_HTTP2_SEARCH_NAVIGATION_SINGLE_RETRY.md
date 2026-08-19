# FırsatAI v23.63.16

## Hepsiburada transient HTTP/2 search navigation single retry

Scope is deliberately narrow. During the v23.63.15 five-product regression, product 143 reached the third Hepsiburada search query and Playwright `page.goto()` failed with `net::ERR_HTTP2_PROTOCOL_ERROR`.

V23.63.16 retries only when all of these are true:

- store is Hepsiburada
- failure occurs during search navigation
- Playwright error contains `ERR_HTTP2_PROTOCOL_ERROR`

The exact same search URL is retried once after a 300 ms bounded pause. The retry preserves Hepsiburada's `domcontentloaded` navigation contract and normal timeout budget.

Not changed:

- SECURITY_CHALLENGE handling or bypass policy
- candidate extraction/scoring
- canonical identity matcher
- price parser/provenance
- verified search-card recovery
- PttAVM v23.63.15 retry
- Turkcell v23.63.14 identity override
- other stores
- database continuity
- price-integrity quarantine

If the second navigation attempt fails, the error is re-raised and the existing fail-closed store failure path remains active.
