from __future__ import annotations
from pathlib import Path
from app.services.store_ecosystem_v13_8_0 import ecosystem_summary, onboarding_template

ROOT = Path(__file__).resolve().parents[2]

def ok(v, m):
    if not v: raise AssertionError(m)
    print(f"OK  {m}")

def main() -> int:
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.8.0','VERSION 13.8.0')
    s=ecosystem_summary()
    ok(s['infrastructure_capacity'] >= 20,'20+ mağaza altyapı kapasitesi mevcut')
    ok(s['product_scraper_ready'] >= 13,'mevcut ürün scraper kayıtları korunuyor')
    ok(s['category_scraper_ready'] >= 8,'mevcut kategori scraper kayıtları korunuyor')
    ok(s['registry_alignment']['aligned'],'merkezi mağaza tanımları runtime registry ile uyumlu')
    ok(all(x['status'] != 'active' or x['product_scraper'] for x in s['stores']),'aktif mağaza scraper olmadan ilan edilmiyor')
    t=onboarding_template('ornek','Örnek Mağaza',['example.com'])
    ok(t['default_status']=='onboarding','yeni mağaza güvenli onboarding durumuyla başlıyor')
    main=(ROOT/'main.py').read_text(encoding='utf-8-sig')
    ok('store_ecosystem_v13_router' in main and 'include_router(store_ecosystem_v13_router)' in main,'store ecosystem router uygulamaya bağlı')
    route=(ROOT/'app/web/store_ecosystem_v13_routes.py').read_text(encoding='utf-8')
    ok('/api/store-ecosystem/v13' in route,'store ecosystem durum API mevcut')
    ok('onboarding-template' in route,'yeni mağaza onboarding şablon API mevcut')
    print('\nFırsatAI v13.8.0 20+ Mağaza Altyapısı smoke test başarılı.')
    return 0

if __name__=='__main__': raise SystemExit(main())
