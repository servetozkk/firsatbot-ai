# FirsatAI v23.62.41

Force-refresh response runtime version metadata is now sourced from `_RUNTIME_VERSION_V236241`.

- Fixes stale `23.62.39` in `/api/dev/v23629/force-deep-refresh/{global_product_id}` response.
- Adds `/api/runtime-identity/v236241`.
- Preserves v23.62.40 N11 3750ms hysteresis guard.
- Preserves v23.62.39 N11 detail HTTP 4.5s soft-cap.
- Preserves v23.62.38 Itopya and v23.62.36 Idefix bounded paths.
- Smoke test inspects the actual force response builder region and rejects stale literals.
