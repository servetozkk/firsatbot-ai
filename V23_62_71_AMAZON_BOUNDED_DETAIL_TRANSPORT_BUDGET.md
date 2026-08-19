# V23.62.71 Amazon Bounded Detail Transport Budget

- v23.62.70 strong-query-first and first authoritative NO_BUYABLE circuit-break are preserved.
- Amazon detail requests timeout is reduced from 30s to 8s.
- Amazon BrowserEngine fallback navigation budget is reduced from 15s to 8s.
- Exact-ASIN recovery, identity gates, price integrity and fail-closed NO_BUYABLE semantics are unchanged.
- Goal: prevent one Amazon candidate from dominating a multi-store force scan for 30-50+ seconds.
