from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.4.2','VERSION 13.4.2')
    route=(ROOT/'app/web/category_center_routes.py').read_text(encoding='utf-8')
    service=(ROOT/'app/services/category_center_service.py').read_text(encoding='utf-8')
    index=(ROOT/'app/templates/category_centers.html').read_text(encoding='utf-8')
    detail=(ROOT/'app/templates/category_center_detail.html').read_text(encoding='utf-8')
    main=(ROOT/'main.py').read_text(encoding='utf-8-sig')
    ok('/kategoriler' in route and '/kategori/{category_slug}' in route,'kategori router ve URL yapısı mevcut')
    ok('category_center_router' in main,'kategori router uygulamaya bağlı')
    ok('breadcrumb' in service and 'canonical' in service,'kategori breadcrumb ve SEO metadata mevcut')
    ok('filter_url' in service and 'sort' in detail,'kategori filtre ve sıralama bağlantısı mevcut')
    ok('product_count' in service and 'store_count' in service and 'brand_count' in service,'kategori istatistikleri mevcut')
    ok('engine_version": "13.4.2' in route,'kategori metadata API sürümü doğru')
    ok('Kategori Merkezleri' in index,'kategori merkezleri arayüzü mevcut')
    print('\nFırsatAI v13.4.2 Kategori Merkezleri smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
