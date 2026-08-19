from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.19',(ROOT/'VERSION').read_text().strip()=='23.63.19'),
 ('VERSION.txt 23.63.19',(ROOT/'VERSION.txt').read_text().strip()=='23.63.19'),
 ('runtime constant v236319','_RUNTIME_VERSION_V236319 = "23.63.19"' in main),
 ('runtime endpoint v236319','/api/runtime-identity/v236319' in main),
 ('soak endpoint v236319','/api/runtime-soak-stability/v236319' in main),
 ('force response exact v236319','"runtime_version": _RUNTIME_VERSION_V236319,\n            "test_only": True' in main),
 ('v23.63.18 curated neutralization preserved','V23.63.18 IDEFIX APPLE IPHONE CURATED 5G-BADGE IDENTITY NEUTRALIZATION' in cross),
 ('canonical evidence label stored','canonical_evidence_label_v236319' in cross),
 ('canonical evidence provenance stored','idefix_curated_5g_neutralized_v236319' in cross),
 ('detail uses canonical evidence label','canonical_evidence_label_v236319 = str(' in repair),
 ('detail carry telemetry','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
 ('display label preserved','"label": candidate_label[:3200]' in cross),
 ('general scorer unchanged','score, reason = _search_result_candidate_score(search_query=search_query, href=clean_url, label=scoring_label_v236318)' in cross),
 ('HB v23.63.16 preserved','ERR_HTTP2_PROTOCOL_ERROR' in cross),
 ('PttAVM v23.63.15 preserved','ERR_HTTP_RESPONSE_CODE_FAILURE' in cross),
 ('Turkcell v23.63.14 preserved','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in repair),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for f in ['main.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/stores/adapters/idefix.py']:
 try:
  ast.parse((ROOT/f).read_text(encoding='utf-8')); checks.append((f'AST {f}',True))
 except Exception as e: checks.append((f'AST {f}: {e}',False))
failed=[name for name,ok in checks if not ok]
for name,ok in checks: print(('OK  ' if ok else 'FAIL ')+name)
if failed: raise SystemExit('V23.63.19 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.19 MASTER smoke OK {len(checks)}/{len(checks)}')
