from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.18',(ROOT/'VERSION').read_text().strip()=='23.63.18'),
 ('VERSION.txt 23.63.18',(ROOT/'VERSION.txt').read_text().strip()=='23.63.18'),
 ('runtime constant v236318','_RUNTIME_VERSION_V236318 = "23.63.18"' in main),
 ('runtime endpoint v236318','/api/runtime-identity/v236318' in main),
 ('soak endpoint v236318','/api/runtime-soak-stability/v236318' in main),
 ('force response exact v236318','"runtime_version": _RUNTIME_VERSION_V236318,\n            "test_only": True' in main),
 ('Idefix v23.63.17 curated recovery preserved','V23.63.17 IDEFIX APPLE IPHONE CURATED-LANDING RECOVERY' in cross),
 ('Idefix curated provenance flag','_idefix_apple_iphone_curated_v236318' in cross),
 ('Idefix 5G badge telemetry','V23.63.18 IDEFIX APPLE IPHONE CURATED 5G-BADGE IDENTITY NEUTRALIZATION' in cross),
 ('Idefix scope Apple exact','str(source_identity_v236318.get("brand") or "") == "apple"' in cross),
 ('Idefix scope phone','str(source_identity_v236318.get("category_mode") or "") == "phone"' in cross),
 ('Idefix scope iPhone family','source_family_v236318.startswith("iphone ")' in cross),
 ('source network must be unspecified','not source_network_v236318' in cross),
 ('candidate badge must be 5g','network_v236318 == "5g"' in cross),
 ('family exact','family_v236318 == source_family_v236318' in cross),
 ('variant exact','variant_v236318 == source_variant_v236318' in cross),
 ('storage exact guard','int(source_storage_v236318) == int(storage_v236318)' in cross),
 ('scoring-only label copy','scoring_label_v236318 = candidate_label' in cross),
 ('general phone scorer unchanged','elif network:\n        return -946, f"telefon farklı ağ varyantı: {network}"' in cross),
 ('HB v23.63.16 preserved','ERR_HTTP2_PROTOCOL_ERROR' in cross),
 ('PttAVM v23.63.15 preserved','ERR_HTTP_RESPONSE_CODE_FAILURE' in cross),
 ('Turkcell v23.63.14 preserved','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in repair),
 ('security bypass disabled','security_challenge_bypass' in main and '"disabled"' in main),
 ('price integrity preserved','price_integrity_quarantine' in main),
]
for rel in ['main.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/stores/adapters/idefix.py']:
    try: ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
    except Exception: checks.append((f'AST {rel}',False))
failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
if failed: raise SystemExit('V23.63.18 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.18 MASTER smoke OK {len(checks)}/{len(checks)}')
