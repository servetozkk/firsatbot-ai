from pathlib import Path
from jinja2 import Environment,FileSystemLoader,select_autoescape
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
 if not v: raise AssertionError(m)
 print('OK ',m)
def main():
 ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.6.3','VERSION 13.6.3')
 from app.services.breadcrumb_service import normalize_breadcrumbs,page_breadcrumbs,product_breadcrumb
 x=normalize_breadcrumbs([('Kategoriler','/kategoriler'),('Laptop',None),('Laptop',None)])
 ok(x[0]['label']=='Ana Sayfa','breadcrumb Ana Sayfa ile başlıyor'); ok(x[-1]['url'] is None,'son breadcrumb öğesi bağlantısız'); ok(len(x)==3,'mükerrer breadcrumb öğeleri temizleniyor')
 p=product_breadcrumb('Lenovo LOQ',category='Laptop',category_url='/kategori/laptop',brand='Lenovo',brand_url='/marka-merkezi/lenovo')
 ok([i['label'] for i in p]==['Ana Sayfa','Kategoriler','Laptop','Markalar','Lenovo','Lenovo LOQ'],'ürün breadcrumb hiyerarşisi doğru')
 env=Environment(loader=FileSystemLoader(str(ROOT/'app/templates')),autoescape=select_autoescape(['html']))
 html=env.from_string('{% from "components/breadcrumbs.html" import render_breadcrumbs %}{{ render_breadcrumbs(items) }}').render(items=page_breadcrumbs(('Kategoriler','/kategoriler'),('Laptop',None)))
 ok('aria-current="page"' in html and '/kategoriler' in html,'breadcrumb bileşeni erişilebilir HTML üretiyor')
 ok('v13-6-3-breadcrumb-style' in (ROOT/'app/templates/public_base.html').read_text(encoding='utf-8'),'merkezi breadcrumb stili mevcut')
 for route in ['category_center_routes.py','brand_center_routes.py','store_center_routes.py','campaign_center_routes.py','coupon_center_routes.py']:
  ok('breadcrumbs_v13' in (ROOT/'app/web'/route).read_text(encoding='utf-8'),f'{route} merkezi breadcrumb context kullanıyor')
 print('\nFırsatAI v13.6.3 Breadcrumb Sistemi smoke test başarılı.')
if __name__=='__main__': main()
