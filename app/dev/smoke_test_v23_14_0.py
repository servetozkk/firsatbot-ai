from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]

def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print('OK ', msg)

check((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip() == '23.14.0', 'VERSION 23.14.0')
main_text=(ROOT/'main.py').read_text(encoding='utf-8')
check('/api/runtime-identity/v2314' in main_text, 'v23.14 runtime endpoint mevcut')

# Gerçek cross-store kaynak dosyasındaki fonksiyonları AST ile yükle; uygulama bağımlılıklarını istemez.
src=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
tree=ast.parse(src)
want={'_fold_search_text','_natural_generic_identity_v2314','_natural_generic_candidate_score_v2314'}
nodes=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
mod=ast.Module(body=nodes,type_ignores=[])
ns={'re':re}
exec(compile(mod,'cross_store_search_service.py','exec'),ns)
identity=ns['_natural_generic_identity_v2314']
score=ns['_natural_generic_candidate_score_v2314']

cases=[
('SECRET OF LOVE yasemin cubuklu oda kokusu 1oo ml','Secret Of Love Yasemin Çubuklu Oda Kokusu 100 ml','https://x/secret-of-love-yasemin-oda-kokusu-100-ml',True),
('Jeven Brus kiss me erkek parfum edp 50 ml','Jeven Brus Kiss Me Erkek Parfüm EDP 50 ml','https://x/jeven-brus-kiss-me-edp-50ml',True),
('Jeven Brus kiss me erkek parfum edp 50 ml','Jeven Brus Kiss Me Erkek Parfüm EDP 100 ml','https://x/jeven-brus-kiss-me-edp-100ml',False),
('Xiaomi redmi 20000 mah powerbank 18w','Xiaomi Redmi 20000 mAh Powerbank 18W','https://x/xiaomi-redmi-20000mah-powerbank',True),
('Xiaomi redmi 20000 mah powerbank 18w','Redmi Pad Pro Uyumlu 20000 mAh Powerbank','https://x/uyumlu-20000mah-powerbank',False),
('ROBO super 4 lu sarjli aku atesleyici lastik sisirici powerbank 150psi','Robo Süper 4lü Şarjlı Akü Ateşleyici Lastik Şişirici 150PSI Kırmızı','https://x/robo-super-4lu-150psi',True),
('ROBO super 4 lu sarjli aku atesleyici lastik sisirici powerbank 150psi','Robo Akü Ateşleyici Lastik Şişirici 120PSI','https://x/robo-120psi',False),
]
for q,label,url,expected in cases:
    ident=identity(q)
    check(ident is not None, f'identity çıkarıldı: {q[:28]}')
    sc,reason=score(identity=ident,href=url,label=label)
    check((sc > 0) == expected, f'card gate {"GREEN" if expected else "RED"}: {reason}')

# Query builder düzeltmesinin kaynakta gerçekten yer aldığını kontrol et.
check('natural_powerbank_v2314' in src and 'add_value("powerbank")' in src, 'powerbank query routing ürün tipini koruyor')

# Detail-stage natural bridge kaynakta ve dispatch sırası legacy matcher öncesinde.
detail=(ROOT/'app/services/category_aware_matcher_v221.py').read_text(encoding='utf-8')
check('def _natural_match_v2314' in detail, 'v23.14 detail-stage natural matcher mevcut')
check(detail.index('natural_v2314 = _natural_profile_v2314(source_product)') < detail.index('if _is_exact_code_accessory_v233(source_product):'), 'natural detail dispatch legacy/accessory-code öncesinde')

# Önceki korumaların kaynakta kaldığını doğrula.
for marker in ('V23.11 laptop kesin red','V23.11 audio kesin red','V22.5 wearable kesin red','V23.6'):
    check(marker in detail, f'koruma preserved: {marker}')

print('OK  FirsatAI v23.14 smoke test tamamlandi')
