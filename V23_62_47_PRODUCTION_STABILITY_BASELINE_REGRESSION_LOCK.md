# FirsatAI v23.62.47 - Production Stability Baseline / Regression Lock

Bu surum yeni performans davranisi eklemez. v23.62.46'da calisan latency ve fail-closed kontratlarini smoke test ile kilitler.

Kilitlenen ana kontratlar:
- N11 strong-first navigation hysteresis: 4250 ms
- N11 weak-first navigation budget: 4500 ms
- N11 detail HTTP soft-cap: 4.5 s
- N11 browser security-challenge bounded recheck: 0.5 s, fail-closed, bypass yok
- Hepsiburada selector-ready search fast-path korunur
- Hepsiburada challenge recheck: tek 1.0 s
- Idefix bounded no-candidate search korunur
- Itopya bounded browser fallback korunur
- Production ingestion davranisi degismez
- Price integrity quarantine korunur

Amaç: sonraki gelistirmelerde bu stabil tabanin istemeden bozulmasini smoke test seviyesinde engellemek.
