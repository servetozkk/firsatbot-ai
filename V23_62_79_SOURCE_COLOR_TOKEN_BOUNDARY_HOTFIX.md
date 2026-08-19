# FirsatAI v23.62.79

## Amaç
Kaynak renk çıkarımında substring kaynaklı yanlış pozitifleri kaldırır. Özellikle `Redmi` içindeki `red` artık `kirmizi` olarak yorumlanmaz.

## Regresyon vakası
`XIAOMI Redmi Note 15 Pro 8 GB 256 GB Akıllı Telefon Titanyum Gri` => `gri`.

## Korunan davranışlar
- v23.62.78 Amazon phone search-card plausibility prefilter
- v23.62.77 bounded identity-reject backup retry
- v23.62.76 Hepsiburada recovery
- security challenge bypass disabled
- price integrity quarantine preserved
