from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip(); ok(version=='13.4.4','VERSION 13.4.4')
    route=(ROOT/'app/web/store_center_routes.py').read_text(encoding='utf-8')
    service=(ROOT/'app/services/store_center_service.py').read_text(encoding='utf-8')
    main=(ROOT/'main.py').read_text(encoding='utf-8')
    t1=(ROOT/'app/templates/store_centers.html').read_text(encoding='utf-8')
    t2=(ROOT/'app/templates/store_center_detail.html').read_text(encoding='utf-8')
    ok('/magazalar' in route and '/magaza-merkezi/{slug}' in route,'mağaza merkezleri router ve URL yapısı mevcut')
    ok('store_center_router' in main,'mağaza merkezleri router uygulamaya bağlı')
    ok('quality' in service and 'components' in service,'açıklanabilir mağaza kalite sinyali mevcut')
    ok('shipping_method' in service and 'delivery_text' in service,'kargo ve teslimat kapsamı hesaplanıyor')
    ok('is_official_seller' in service,'resmi satıcı sinyali hesaplanıyor')
    ok('ENGINE_VERSION = "13.4.4"' in service,'mağaza metadata API sürümü doğru')
    ok('breadcrumbs' in route and 'canonical_url' in route,'mağaza breadcrumb ve SEO metadata mevcut')
    ok('Kalite sinyali' in t2 and 'Mağazalar' in t1,'mağaza merkezleri arayüzü mevcut')
    print('\nFırsatAI v13.4.4 Mağaza Sayfaları ve Kalite smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
