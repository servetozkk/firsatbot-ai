from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
svc = (ROOT / 'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
main = (ROOT / 'main.py').read_text(encoding='utf-8')
ops = (ROOT / 'app/ops/data_continuity_v218.py').read_text(encoding='utf-8')
route = (ROOT / 'app/web/catalog_feed_v218_routes.py').read_text(encoding='utf-8')

checks = {
    'runtime_v218': '/api/runtime-identity/v218' in main,
    'router_v218': 'catalog_feed_v218_router' in main,
    'failed_offer_retention': '_restore_failed_store_offers' in svc and 'snapshot = _active_offer_snapshot' in svc,
    'crawler_offer_separation': 'crawler_state_is_separate_from_offer_state' in svc,
    'tracked_searchable_split': 'tracked_store_count' in svc and 'searchable_store_count' in svc,
    'source_store_excluded': "searchable_codes = [code for code in all_codes if code != source_code]" in svc,
    'legacy_recovery': '_recover_global_offers_from_legacy' in svc and 'sync_global_offer' in svc,
    'data_continuity': 'FIRSATAI_DATA_CONTINUITY' in ops and 'src.backup(dst)' in ops,
    'v218_status_route': "prefix='/api/catalog-feed/v218'" in route,
}
failed = [k for k, v in checks.items() if not v]
for key, ok in checks.items():
    print(('OK  ' if ok else 'FAIL'), key)
if failed:
    raise SystemExit('V21.8 smoke failed: ' + ', '.join(failed))
print('OK  V21.8 smoke test passed')
