FirsatAI v23.63.15 - PTTAVM TRANSIENT SEARCH NAVIGATION SINGLE RETRY
===================================================================

Amaç
----
V23.63.14 Turkcell iOS canonical candidate identity düzeltmesini ve tüm eski
korumaları aynen muhafaza ederek yalnız PttAVM search navigation sırasında
Playwright tarafından döndürülen net::ERR_HTTP_RESPONSE_CODE_FAILURE transient
hatasına aynı URL üzerinde tek bounded retry ekler.

Scope
-----
- Sadece store_code=pttavm
- Sadece ERR_HTTP_RESPONSE_CODE_FAILURE
- Toplam en fazla 2 navigation denemesi
- İkinci hata sonrası fail-closed / mevcut exception davranışı
- Query, candidate extraction, identity matcher ve fiyat parser değişmez

Korunanlar
----------
- v23.63.14 Turkcell iOS canonical candidate identity override
- v23.63.10 PttAVM seller/brand ayrımı
- Turkcell price provenance
- Amazon, N11, idefix, Beymen ve diğer mağaza davranışları
- DB continuity / price integrity quarantine / security challenge policy

Telemetry
---------
V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY [...]
V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY EXHAUSTED [...]
