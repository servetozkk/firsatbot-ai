# FirsatAI v23.63.47

## Scope

Narrow provenance residue fix on top of v23.63.46. The production audit found one remaining proven pseudo model-code form: `kapasitesi90` on GlobalProduct 83 and its linked variant.

## Behavior

- `kapasitesiNN` is rejected as a specification-derived pseudo model code.
- Existing GlobalProduct and GlobalProductVariant residue is cleared during startup.
- No automatic canonical merge is performed.
- No variant-key rewrite is performed.
- B0 Amazon ASIN and legitimate SKU/model codes remain valid.
- v23.63.41-v23.63.46 integrity and quarantine behavior is preserved.
