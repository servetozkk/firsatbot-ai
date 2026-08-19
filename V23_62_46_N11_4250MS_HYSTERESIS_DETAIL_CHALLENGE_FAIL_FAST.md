# FirsatAI v23.62.46

## Amaç
N11 localhost varyansında iki pahalı dead-end'i sınırlar.

- Strong brand+model ilk sorgu hysteresis: 4000 ms -> 4250 ms.
- N11 detail HTTP 4.5 sn soft-cap korunur.
- HTTP fallback browser Cloudflare/security challenge görürse server-mode recheck 3.0 sn yerine 0.5 sn.
- Challenge bypass yoktur; sonuç fail-closed kalır ve kalan aday akışı mevcut kurallarla devam eder.
- Hepsiburada v23.62.45 selector-ready fast-path aynen korunur.
- Identity, accessory, detail evidence ve price-integrity kuralları değiştirilmez.
