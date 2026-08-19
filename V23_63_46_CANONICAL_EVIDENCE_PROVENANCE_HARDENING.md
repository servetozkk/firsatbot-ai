# FirsatAI v23.63.46

## Canonical Evidence Provenance Hardening — No Automatic Merge

This release deliberately does **not** merge duplicate GlobalProduct rows.
The v23.63.46 raw-evidence audit showed that brand+family duplicates can hide
real SKU differences such as storage, network, Plus/Ultra/Pro/FE, and series.

Changes:
- reject proven specification-derived pseudo model codes such as `araligi3500-4000`, `kapasite0-15`, `uzunlugu110-120`, `dci-p3`, and `tr63`;
- preserve B0-prefixed Amazon ASIN values;
- sanitize model_code on normal global-catalog writes, preferred canonical overrides, and bulk identity writes;
- clean existing GlobalProduct and GlobalProductVariant pseudo model-code residue at startup;
- never rewrite variant_key in this release;
- never auto-merge duplicate canonical rows in this release; raw-evidence consensus remains mandatory.

Preserved:
- v23.63.45 unified quarantine lifecycle;
- v23.63.44 source/canonical contradiction quarantine;
- v23.63.43 counter integrity;
- v23.63.42 accessory identity guard;
- v23.63.41 raw-scoped variant referential convergence.
