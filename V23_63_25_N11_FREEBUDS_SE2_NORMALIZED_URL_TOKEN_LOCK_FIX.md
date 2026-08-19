# FirsatAI v23.63.25

Scope: N11 FreeBuds SE 2 white verified search-card recovery only.

Fix: `_v236283_fold()` converts URL hyphens to spaces. v23.63.24 compared folded URLs against hyphenated tokens, so the white URL lock could never pass. v23.63.25 compares normalized tokens (`freebuds se 2`, `ceramic white`, `seramik beyaz`) while preserving the same score, white-color, black/blue exclusion, tight price-cluster, price-integrity, and no-bypass gates.
