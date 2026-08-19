# FirsatAI v23.63.48

## Raw-consensus atomic canonical convergence

This release converts the validated v23.63.48 RAM-only merge simulation into a fail-closed startup convergence.

### Scope

Only nine pre-audited canonical pairs are eligible. Brand+family similarity is **not** an automatic merge rule and no future product is auto-merged from this fixed plan.

Approved survivor <- retire pairs:

- 78 <- 60 (Apple iPhone 15 128 GB)
- 106 <- 59 (Apple iPhone 16 128 GB)
- 58 <- 57 (Apple iPhone 17 Pro 256 GB)
- 62 <- 61 (Apple iPhone 17 256 GB)
- 134 <- 79 (Apple iPhone 17 Pro Max 256 GB)
- 93 <- 70 (Samsung Fold8 Ultra 1 TB)
- 91 <- 73 (Samsung Fold8 1 TB)
- 97 <- 75 (Samsung Galaxy A26 256 GB)
- 67 <- 102 (Xiaomi 17 12/512 5G)

### Safety gates

- Raw evidence must still agree with the expected brand, family and marketed variant class.
- Pro, Pro Max, Ultra, Plus/+ and standard are hard identity boundaries.
- Explicit RAM, storage or network conflicts reject a pair.
- At least two positive SKU dimensions are required.
- Existing alerts, bulk-identity references or review references fail closed and skip the affected pair.
- Variant target keys are computed before writes; intra-product collisions are collapsed before unique-key rewrites.
- RawProduct, GlobalOffer and GlobalOfferPriceHistory variant/product references are relinked before deleting retired variants/products.
- Survivor canonical fields are only enriched when missing; existing values are never overwritten.
- Counters are rebuilt after merges.
- Foreign keys, duplicate variant keys, variant/product referential integrity, counters, quarantine state and retire-row removal are checked before commit.
- Any post-write health-gate failure rolls back the transaction.

### Preserved

- v23.63.47 model-code provenance residue lock
- v23.63.45 unified quarantine lifecycle
- v23.63.44 source/canonical contradiction quarantine
- v23.63.43 global counter integrity
- v23.63.41 variant referential convergence
- security challenge bypass disabled
