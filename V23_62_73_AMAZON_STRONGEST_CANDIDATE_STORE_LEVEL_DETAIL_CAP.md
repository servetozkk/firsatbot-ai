# FırsatAI v23.62.73 — Amazon Strongest-Candidate Store-Level Detail Cap

- v23.62.72 18s shared Amazon detail/recovery/browser deadline is preserved.
- Root cause: each cross-store Amazon candidate created a fresh scraper and therefore a fresh 18s deadline; non-NO_BUYABLE failures could still permit candidate 2/3 and inflate store latency to ~36-40s.
- Amazon strong-query-first ordering is preserved. Only the strongest first Amazon detail candidate is allowed into the expensive detail chain.
- If that candidate cannot produce a safe buyable offer, the scan fails closed instead of trying weaker recommendation candidates.
- N11, phone accessory hard rejects, price integrity, security fail-closed, 11-store budget and production ingestion behavior are unchanged.
