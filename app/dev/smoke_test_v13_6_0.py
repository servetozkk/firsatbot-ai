from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app.services.seo_url_service import slugify,product_url,parse_product_path

def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)

def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.6.0','VERSION 13.6.0')
    ok(slugify('İPhone 16 Pro 256 GB')=='iphone-16-pro-256-gb','Türkçe karakterli ürün adı slug oluşturuyor')
    url=product_url('Lenovo LOQ 15 RTX 4060','abc123')
    ok(url=='/urun/lenovo-loq-15-rtx-4060-p-abc123','SEO ürün URL yapısı doğru')
    key,slug=parse_product_path('lenovo-loq-15-rtx-4060-p-abc123')
    ok(key=='abc123' and slug=='lenovo-loq-15-rtx-4060','SEO ürün URL ayrıştırılıyor')
    route=(ROOT/'app/web/global_product_routes.py').read_text(encoding='utf-8')
    ok('RedirectResponse' in route and 'status_code=301' in route,'eski ürün URL 301 kanonik adrese yönleniyor')
    base=(ROOT/'app/templates/public_base.html').read_text(encoding='utf-8')
    ok('canonical_url|default' in base,'canonical URL merkezi template tarafından kullanılıyor')
    detail=(ROOT/'app/templates/product_group_detail_v4.html').read_text(encoding='utf-8')
    ok('seo_description' in detail and 'seo_title' in detail,'ürün sayfası SEO metadata kullanıyor')
    print('\nFırsatAI v13.6.0 SEO URL Yapısı smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
