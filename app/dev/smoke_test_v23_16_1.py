from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,msg):
    if not cond: raise AssertionError(msg)
    print('OK ',msg); checks.append(msg)
assert (ROOT/'VERSION').read_text().strip()=='23.16.1'
main=(ROOT/'main.py').read_text(encoding='utf-8')
prod=(ROOT/'app/services/production_ingestion_v220_service.py').read_text(encoding='utf-8')
smart=(ROOT/'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
bulk=(ROOT/'app/services/bulk_ingestion_v232_service.py').read_text(encoding='utf-8')
ok('/api/runtime-identity/v23161' in main,'v23.16.1 runtime endpoint mevcut')
start=smart.index('def smart_refresh_product(')
end=smart.find('\ndef ', start+10)
refresh=smart[start:end if end!=-1 else None]
ok('circuit_skipped: list[dict[str, Any]] = []' in refresh,'circuit_skipped smart_refresh scope icinde')
life_start=smart.index('def get_offer_lifecycle_status(')
life_end=smart.index('def smart_refresh_product(', life_start)
lifecycle=smart[life_start:life_end]
ok('allowed_store_codes' not in lifecycle and 'circuit_skipped' not in lifecycle,'lifecycle status refresh-only degiskenlerden arindirildi')
ok('_FAST_STORE_TIER' in prod,'fast store tier korundu')
ok('fast_ingest: bool = True' in prod,'production ingestion fast default korundu')
ok('parallel_workers=6 if fast_ingest' in prod,'fast store workers 6 korundu')
ok('_deep_executor' in prod and '_background_deep_refresh' in prod,'background deep refresh korundu')
ok('_STORE_CIRCUIT_UNTIL' in smart and '_STORE_CIRCUIT_MINUTES = 10' in smart,'10 dk circuit breaker korundu')
ok('fast_ingest=False' in bulk,'stress/bulk full scan korundu')
ok('price_integrity_quarantine' in main,'fiyat karantinasi korundu')
print(f'OK  FirsatAI v23.16.1 smoke test tamamlandi ({len(checks)}/10)')
