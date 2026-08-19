# V23.63.11 — Force refresh runtime version coherence

V23.63.10 PttAVM seller/manufacturer fix is preserved. The only behavioral change is that `/api/dev/v23629/force-deep-refresh/{global_product_id}` now reports the same active runtime version as `/api/runtime-identity/v236311`.

This closes the observed v23.63.10 mismatch where runtime identity returned 23.63.10 but force-deep-refresh returned 23.63.09.
