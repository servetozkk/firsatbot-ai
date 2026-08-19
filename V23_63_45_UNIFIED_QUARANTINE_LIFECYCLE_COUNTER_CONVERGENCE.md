# FirsatAI v23.63.45

## Unified Quarantine Lifecycle + Counter Convergence

This release does not change quarantine decisions. It normalizes every existing
`GlobalOffer.lifecycle_status == QUARANTINED` row to the fail-closed serving state:

- `is_active = false`
- `is_hidden = true`

Price-integrity quarantine now creates that same state directly. After the price
integrity startup audit, v23.63.45 runs a final convergence pass and recomputes
`GlobalProduct.active_offer_count` strictly from serving-eligible offers.

Source identity v23.63.44, variant v23.63.41, accessory v23.63.42 and model-code
v23.63.43 policies are preserved.
