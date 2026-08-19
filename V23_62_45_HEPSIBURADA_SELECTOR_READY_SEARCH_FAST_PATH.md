# FirsatAI v23.62.45

Hepsiburada search-page product-card readiness now enables a safe fast path: when a real product-card selector is attached, use a 150 ms settle and skip networkidle. If readiness is not observed, the existing v23.62.20 settle/network fallback is preserved. Candidate extraction, detail identity, price integrity, persistent security-challenge detection and the v23.62.42 single 1 second fail-closed recheck are unchanged.
