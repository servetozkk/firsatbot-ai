# FirsatAI v23.62.28

N11 first model-first query navigation variance guard.

- Only N11 query #1 is bounded to 4500 ms when fallback queries exist.
- Timeout remains fail-closed and continues to the existing stronger brand+model query.
- Subsequent N11 queries keep the existing full navigation budget.
- v23.62.26 selector-ready fast path is preserved.
- v23.62.27 Vatan fast path is preserved.
- Canonical identity, detail gate, accessory/bundle rejects, price integrity, quarantine, force single-flight/cooldown, DB guards and security challenge policy are unchanged.
