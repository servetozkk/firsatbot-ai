from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
 if not v: raise AssertionError(m)
 print('OK ',m)
def main():
 ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.4.3','VERSION 13.4.3')
 r=(ROOT/'app/web/brand_center_routes.py').read_text(encoding='utf-8'); s=(ROOT/'app/services/brand_center_service.py').read_text(encoding='utf-8'); t=(ROOT/'app/templates/brand_center_detail.html').read_text(encoding='utf-8')
 ok("/markalar" in r and "/marka-merkezi/{brand_slug}" in r,'marka merkezleri router ve URL yapısı mevcut')
 ok('brand_center_router' in (ROOT/'main.py').read_text(encoding='utf-8'),'marka merkezleri router uygulamaya bağlı')
 ok('breadcrumb' in s and 'canonical' in s,'marka breadcrumb ve SEO metadata mevcut')
 ok('series' in s and 'categories' in s,'marka seri ve kategori kırılımı mevcut')
 ok('filter_url' in s and 'sort' in t,'marka filtre ve sıralama bağlantısı mevcut')
 ok("engine_version':'13.4.3" in r.replace(' ',''),'marka metadata API sürümü doğru')
 ok('Marka Merkezleri' in (ROOT/'app/templates/brand_centers.html').read_text(encoding='utf-8'),'marka merkezleri arayüzü mevcut')
 print('\nFırsatAI v13.4.3 Marka Merkezleri smoke test başarılı.'); return 0
if __name__=='__main__': raise SystemExit(main())
