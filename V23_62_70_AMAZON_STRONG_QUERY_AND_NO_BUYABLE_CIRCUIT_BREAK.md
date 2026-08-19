# FirsatAI v23.62.70

Amazon-only multi-product latency hotfix.

- Preserves v23.62.69 phone accessory hard reject.
- Amazon uses the full canonical search_query before broad brand/model fallbacks.
- After the first authoritative `NO_BUYABLE_OFFER` (requests + exact-ASIN recovery + bounded browser fallback exhausted), remaining Amazon candidates are not sent through another browser-heavy detail cycle.
- Existing identity, color, storage, price-integrity and security fail-closed policies are unchanged.
