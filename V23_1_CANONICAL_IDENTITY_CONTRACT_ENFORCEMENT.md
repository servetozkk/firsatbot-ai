# FırsatAI v23.1.0 — Canonical Identity Contract Enforcement

v23.0 status çıktısında Xiaomi Redmi Watch 5 Active kaydının
`identity_v3:brand=xiaomi|family=redmi watch 5` seviyesine düştüğü görüldü.

Kök neden:
- wearable startup convergence eski `identity_source` metnini,
  canonical_name/model içindeki daha güçlü `Active` kanıtından önce kabul ediyordu.

v23.1:
- identity_source, model ve canonical_name ayrı ayrı analiz edilir.
- En güçlü kimlik kazanır: family + explicit variant > family-only.
- `Active`, `Lite`, `Pro`, `Ultra`, `Classic` açıkça varsa variant düşürülemez.
- Eski variant'sız wearable kayıt, metadata yalnız tek ve aynı explicit varyantı
  doğruluyorsa aynı ID korunarak canonical identity'ye promote edilir.
- Lifecycle status `identity_contract_violation_count` alanını raporlar.
- Duplicate guard ve Amazon NO_BUYABLE_OFFER davranışları korunur.

Beklenen Redmi Watch mapping:
`identity_v3:brand=xiaomi|family=redmi watch 5|variant=active`
canonical_key=`8d1834f8e65b9dbeb8221919d6fc4ca8`
