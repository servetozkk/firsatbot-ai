# FirsatAI v23.62.59

N11 detail HTTP latency tail için transport-level connection reuse.

- N11 registry/dedicated-lane scraper instance boyunca tek `requests.Session` kullanır.
- HTTPS adapter pool size 2; keep-alive/TCP-TLS reuse amaçlıdır.
- N11 detail HTTP timeout 4.5 sn korunur.
- HTML/security/identity/price-integrity kabul kuralları değişmez.
- N11 dışı mağazalarda request-lifetime session davranışı korunur.
- Telemetry: `V23.62.59 N11 DETAIL HTTP CONNECTION`.
