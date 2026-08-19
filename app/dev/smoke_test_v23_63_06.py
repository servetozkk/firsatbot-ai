from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
main = (ROOT / 'main.py').read_text(encoding='utf-8')
repair = (ROOT / 'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
smart = (ROOT / 'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
retail = (ROOT / 'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
force = main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]

checks = [
    ('VERSION 23.63.06', (ROOT/'VERSION').read_text().strip() == '23.63.06'),
    ('VERSION.txt 23.63.06', (ROOT/'VERSION.txt').read_text().strip() == '23.63.06'),
    ('runtime endpoint v236306', '/api/runtime-identity/v236306' in main),
    ('soak endpoint v236306', '/api/runtime-soak-stability/v236306' in main),
    ('force runtime v236306', '"runtime_version": _RUNTIME_VERSION_V236306' in force),
    ('stable source selector preserved', 'def _stable_source_raw_v236304' in repair),
    ('source anchor oldest ordering', 'RawProduct.created_at.asc(), RawProduct.id.asc()' in repair),
    ('canonical color anchor', 'canonical-name-color-oldest-match' in repair),
    ('variant color fallback', 'oldest-explicit-variant-color' in repair),
    ('source anchor telemetry preserved', 'V23.63.04 SOURCE VARIANT ANCHOR:' in repair),
    ('latest raw no longer authoritative', 'newest-row return value define the next force-refresh source' in repair),
    ('Turkcell protected force code preserved', 'protected_force_codes_v236304 = ("n11", "turkcellpasaj")' in smart),
    ('Turkcell force inclusion telemetry preserved', 'V23.63.04 TURKCELL FORCE DUE-SET INCLUSION:' in smart),
    ('protected stores never dropped', 'code_v236268 not in set(protected_force_codes_v236304)' in smart),
    ('budget log has Turkcell', "turkcell_present={'turkcellpasaj' in searchable_codes}" in smart),
    ('Turkcell v303 price provenance preserved', 'V23.63.03 TURKCELL PRICE PROVENANCE LOCK' in retail),
    ('constructor old_price', 'old_price=None' in repair),
    ('constructor rating', 'rating=None' in repair),
    ('constructor review_count', 'review_count=None' in repair),
    ('constructor seller', 'seller=""' in repair),
    ('constructor image', 'image=None' in repair),
    ('security bypass disabled', '"security_challenge_bypass": "disabled"' in main),
    ('price integrity preserved', '"price_integrity_quarantine": "preserved"' in main),
]
failed=[]
for label, ok in checks:
    print(('OK   ' if ok else 'FAIL ')+label)
    if not ok: failed.append(label)

for rel in [
    'main.py',
    'app/services/multi_store_offer_repair_v14_service.py',
    'app/services/smart_catalog_refresh_v218_service.py',
    'app/scrapers/retail_stores.py',
]:
    try:
        ast.parse((ROOT/rel).read_text(encoding='utf-8'))
        print('OK   AST', rel)
    except Exception as exc:
        print('FAIL AST', rel, exc)
        failed.append('AST '+rel)

if failed:
    raise SystemExit('V23.63.06 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.06 MASTER smoke OK {len(checks)+4}/{len(checks)+4}')
