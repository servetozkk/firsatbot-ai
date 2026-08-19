from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,msg):
    if not cond: raise AssertionError(msg)
    print('OK ',msg); checks.append(msg)
assert (ROOT/'VERSION').read_text().strip()=='23.16.0'
main=(ROOT/'main.py').read_text(encoding='utf-8')
prod=(ROOT/'app/services/production_ingestion_v220_service.py').read_text(encoding='utf-8')
smart=(ROOT/'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
bulk=(ROOT/'app/services/bulk_ingestion_v232_service.py').read_text(encoding='utf-8')
ok('/api/runtime-identity/v2316' in main,'v23.16 runtime endpoint mevcut')
ok('_FAST_STORE_TIER' in prod,'fast store tier mevcut')
ok('fast_ingest: bool = True' in prod,'production ingestion fast default')
ok('max_workers=4' in prod,'ürün ingestion concurrency 4')
ok('_deep_executor' in prod and '_background_deep_refresh' in prod,'background deep refresh mevcut')
ok('parallel_workers=6 if fast_ingest' in prod,'fast store workers 6')
ok('allowed_store_codes=_FAST_STORE_TIER if fast_ingest else None' in prod,'fast tier routing aktif')
ok('fast_mode=bool(fast_ingest)' in prod,'fast search timeout mode aktif')
ok('_STORE_CIRCUIT_UNTIL' in smart and '_STORE_CIRCUIT_MINUTES = 10' in smart,'10 dk circuit breaker mevcut')
ok("refresh_mode': 'FAST' if fast_mode else 'DEEP'" in smart,'refresh mode gözlemlenebilir')
ok('fast_ingest=False' in bulk,'stress/bulk full scan korunuyor')
ok('navigation_timeout = 25_000 if self.fast_mode else 60_000' in cross,'fast navigation timeout korunuyor')
ok('price_integrity_quarantine' in main,'fiyat karantinası runtime contractta korunuyor')
print(f'OK  FirsatAI v23.16 smoke test tamamlandi ({len(checks)}/13)')
