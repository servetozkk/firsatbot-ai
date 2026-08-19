from pathlib import Path
import ast, re
ROOT = Path(__file__).resolve().parents[2]
service_path = ROOT/'app/services/cross_store_search_service.py'
service = service_path.read_text(encoding='utf-8')
generic = (ROOT/'app/scrapers/generic_store.py').read_text(encoding='utf-8')
browser = (ROOT/'app/services/browser_engine.py').read_text(encoding='utf-8')
main = (ROOT/'main.py').read_text(encoding='utf-8')
assert (ROOT/'VERSION').read_text(encoding='utf-8').strip() == '21.5.0'
assert '/api/runtime-identity/v215' in main
assert 'explicit-url-or-title-variant-wins-over-card-context' in main
assert 'url_variant = _candidate_variant_after_family' in service
assert 'candidate_variant == suffix' in service
assert 'SECURITY_CHALLENGE' in service
assert 'max_attempts = 1 if self.config.code == "n11" else 2' in generic
assert '3.0 if self.config.code == "n11" else None' in generic
assert 'attention required' in generic and 'cloudflare' in generic
assert 'verification_wait_seconds' in browser

# Yalnızca saf ön eleme fonksiyonlarını AST'den çıkarıp gerçek örneklerle test et.
tree = ast.parse(service)
needed = {
    '_fold_search_text', '_extract_search_hardware', '_query_identity_tokens',
    '_candidate_variant_after_family', '_search_result_candidate_score'
}
body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in needed]
module = ast.Module(body=body, type_ignores=[])
ns = {'re': re}
exec(compile(module, str(service_path), 'exec'), ns)
score = ns['_search_result_candidate_score']
query = 'ASUS x1504va bq5391 8GB RAM 512GB SSD 120u'

# Kirli kart metni BQ5391 içerse bile URL açıkça BQ3970W ise kesin red.
s1, r1 = score(
    search_query=query,
    href='https://www.n11.com/urun/asus-vivobook-15-x1504va-bq3970w-core-5-120u-8-gb-512-gb-ssd-156-w11h-dizustu-bilgisayar-116080985',
    label='ASUS X1504VA-BQ3970W 8GB 512GB ... başka kart ASUS X1504VA-BQ5391',
)
assert s1 == -950 and 'bq3970w' in r1

# Amazon NJ3665 de kaynak BQ5391 olarak kabul edilemez.
s2, r2 = score(
    search_query=query,
    href='https://www.amazon.com.tr/dp/B0BWXC1S47',
    label='Asus VivoBook 15 X1504VA-NJ3665 Core 5 120U 8GB 512SSD 15.6 FHD',
)
assert s2 == -950 and 'nj3665' in r2

# Doğru açık varyant pozitif kalmalı.
s3, r3 = score(
    search_query=query,
    href='https://ornek.com/asus-vivobook-15-x1504va-bq5391',
    label='ASUS Vivobook 15 X1504VA-BQ5391 Core 5 120U 8GB RAM 512GB SSD',
)
assert s3 >= 300, (s3, r3)
print('OK v21.5 variant-first + N11 security smoke')
