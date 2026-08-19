from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
main = (ROOT / 'main.py').read_text(encoding='utf-8')
repair = (ROOT / 'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
smart = (ROOT / 'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
retail = (ROOT / 'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
force = main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]

checks = [
    ('VERSION 23.63.05', (ROOT/'VERSION').read_text().strip() == '23.63.05'),
    ('runtime endpoint v236305', '/api/runtime-identity/v236305' in main),
    ('soak endpoint v236305', '/api/runtime-soak-stability/v236305' in main),
    ('force runtime v236305', '"runtime_version": _RUNTIME_VERSION_V236305' in force),
    ('stable source selector', 'def _stable_source_raw_v236305' in repair),
    ('source anchor oldest ordering', 'RawProduct.created_at.asc(), RawProduct.id.asc()' in repair),
    ('canonical color anchor', 'canonical-name-color-oldest-match' in repair),
    ('variant color fallback', 'oldest-explicit-variant-color' in repair),
    ('source anchor telemetry', 'V23.63.05 SOURCE VARIANT ANCHOR:' in repair),
    ('latest raw no longer authoritative', 'newest-row return value define the next force-refresh source' in repair),
    ('Turkcell protected force code', 'protected_force_codes_v236305 = ("n11", "turkcellpasaj")' in smart),
    ('Turkcell force inclusion telemetry', 'V23.63.05 TURKCELL FORCE DUE-SET INCLUSION:' in smart),
    ('protected stores never dropped', 'code_v236268 not in set(protected_force_codes_v236305)' in smart),
    ('budget log has Turkcell', "turkcell_present={'turkcellpasaj' in searchable_codes}" in smart),
    ('Turkcell v303 price provenance preserved', 'V23.63.03 TURKCELL PRICE PROVENANCE LOCK' in retail),
    ('security bypass disabled', '"security_challenge_bypass": "disabled"' in main),
    ('price integrity preserved', '"price_integrity_quarantine": "preserved"' in main),
]
for label, ok in checks:
    if not ok:
        raise SystemExit('FAIL ' + label)
    print('OK  ', label)

for rel in [
    'main.py',
    'app/services/multi_store_offer_repair_v14_service.py',
    'app/services/smart_catalog_refresh_v218_service.py',
    'app/scrapers/retail_stores.py',
]:
    ast.parse((ROOT/rel).read_text(encoding='utf-8'))
    print('OK   AST', rel)

print(f'V23.63.05 MASTER smoke OK {len(checks)+4}/{len(checks)+4}')

# V23.63.05 constructor compatibility regression
svc_text = (ROOT / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
for needle in ["old_price=None", "rating=None", "review_count=None", "seller=\"\"", "image=None"]:
    check(f"source-anchor Product ctor field {needle}", needle in svc_text)
