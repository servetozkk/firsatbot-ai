from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,msg):
    assert cond,msg
    checks.append(msg); print('OK ',msg)
prod=(ROOT/'app/services/production_ingestion_v220_service.py').read_text(encoding='utf-8')
main=(ROOT/'main.py').read_text(encoding='utf-8')
bulk=(ROOT/'app/services/bulk_ingestion_v232_service.py').read_text(encoding='utf-8')
ok((ROOT/'VERSION').read_text().strip()=='23.17.0','VERSION 23.17.0')
ok('/api/runtime-identity/v2317' in main,'v23.17 runtime endpoint mevcut')
ok('_EARLY_READY_STORE_TIER = {"pazarama", "teknosa"}' in prod,'primary early-ready tier tanimli')
ok('allowed_store_codes=_EARLY_READY_STORE_TIER if fast_ingest else None' in prod,'FAST user scan primary tier ile sinirli')
ok('deferred_store_codes=sorted(_FAST_STORE_TIER - _EARLY_READY_STORE_TIER)' in prod,'kalan fast storelar backgrounda devrediliyor')
ok('ready_policy' in prod and 'PRIMARY_TIER_THEN_BACKGROUND' in prod,'task ready policy raporlaniyor')
ok('_deep_executor.submit(_background_deep_refresh' in prod,'deep refresh background korunuyor')
ok('parallel_workers=6 if fast_ingest' in prod,'FAST worker 6 korunuyor')
ok('fast_ingest=False' in bulk,'stress/bulk full scan korunuyor')
ok('price_integrity' in prod.lower(),'price integrity pipeline korunuyor')
print(f'OK  FirsatAI v23.17 smoke test tamamlandi ({len(checks)}/10)')
