# FirsatAI v23.62.26

Hedef: v23.62.25 force-refresh guard davranışını korurken force endpoint response metadata sürümünü güncellemek ve N11 selector-ready yolundaki gereksiz post-ready beklemeyi azaltmak.

- Force test endpoint başarılı response `runtime_version`: `23.62.26`.
- N11 ürün selector'u hazırsa: 150 ms kısa hydration settle + networkidle beklemesini atlama.
- N11 selector hazır değilse v23.62.21 settle/network fallback aynen korunur.
- Identity/detail gate, accessory/bundle reject, price integrity quarantine değişmedi.
- v23.62.25 single-flight + 409 active + 429 cooldown guard korunur.
- Production ingestion davranışı değişmedi.
- Security challenge bypass yoktur.
