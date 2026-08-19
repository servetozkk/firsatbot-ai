# FirsatAI v23.62.44

Hepsiburada kalici SECURITY_CHALLENGE yoluna davranis degistirmeyen faz telemetry eklendi.

Olculen fazlar:
- search
- candidate_extraction
- detail_goto
- challenge_detection
- challenge_recheck
- cleanup
- total

Korunan davranislar:
- v23.62.42 tek 1000 ms bounded challenge recheck
- security challenge bypass kapali
- v23.62.43 N11 strong-first 4000 ms hysteresis
- N11 detail HTTP 4.5 s soft cap
- Itopya/IdeFix/Pazarama/Trendyol/Vatan mevcut korumalar
