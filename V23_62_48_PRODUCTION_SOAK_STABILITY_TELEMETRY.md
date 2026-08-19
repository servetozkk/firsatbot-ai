# FırsatAI v23.62.48 — Production Soak & Stability Telemetry

Behavior-preserving observability release based on the v23.62.47 production baseline.

- Rolling in-memory window: last 50 localhost force refresh runs.
- Tracks total latency, offer count, store success/failure counts.
- Per-store success rate, avg/min/max latency, failure-class distribution.
- Regression alarms for offer count, success-store count, and N11 success contract.
- No scraper threshold, candidate gate, price-integrity, challenge, or production-ingestion behavior is changed.
- Telemetry resets when the API process restarts.

Endpoint: `/api/runtime-soak-stability/v236248`
