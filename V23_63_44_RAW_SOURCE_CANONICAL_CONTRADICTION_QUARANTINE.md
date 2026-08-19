# FirsatAI v23.63.44 — Raw Source / Canonical Contradiction Quarantine

Bu sürüm v23.63.43 davranışını korur ve bağımsız kaynak kanıtının canonical ürünle güçlü biçimde çeliştiği teklifleri fail-closed karantinaya alır.

## Politika
- Semantik URL taşıyan mağazalarda raw başlık ürün sınıfı ile URL ürün sınıfı açıkça çelişirse teklif karantinaya alınır.
- Amazon `/dp/ASIN` gibi opaque URL'ler semantic mismatch kanıtı olarak kullanılmaz.
- `canonical_override=true` kayıtlarında raw başlık ile canonical arasında açık RTX GPU çelişkisi veya aynı-prefix model serisi çelişkisi (örn. X60 -> X55) karantina için güçlü kanıttır.
- Tek başına brand/model parser farkı karantina oluşturmaz.
- Yeni quarantine tablosu yoktur. RawProduct `reconciliation_status/reconciliation_error`, GlobalOffer `is_active/is_hidden/lifecycle_status/duplicate_reason` alanları kullanılır.
- GlobalOffer silinmez; `is_active=False`, `is_hidden=True`, `lifecycle_status=QUARANTINED` olur.
- Production reconcile guard price-history yazımından önce çalışır ve RawProduct karantina durumu sonradan MATCHED ile ezilmez.

## Korunan önceki invariantlar
- v23.63.40 raw authoritative marketplace metadata
- v23.63.41 raw-scoped variant binding / zero variant drift
- v23.63.42 accessory identity guard
- v23.63.43 model-code provenance ve authoritative child counters
- price integrity quarantine ve security bypass disabled
