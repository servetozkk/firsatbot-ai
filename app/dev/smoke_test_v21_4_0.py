from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
service=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
registry=(ROOT/'app/stores/adapters/registry.py').read_text(encoding='utf-8')
main=(ROOT/'main.py').read_text(encoding='utf-8')
assert (ROOT/'VERSION').read_text(encoding='utf-8').strip() == '21.4.0'
assert '/api/runtime-identity/v214' in main
assert 'def _store_search_queries' in service
assert 'def _store_search_url' in service
assert 'definition.code == "vatan"' in service
assert 'min(3, self.candidate_limit)' in service
assert 'PAZARAMA_ADAPTER' in registry and 'IDEFIX_ADAPTER' in registry
assert '_is_same_product' in service and 'validate_variant' in service
print('OK v21.4 store coverage static smoke')
