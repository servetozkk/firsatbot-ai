from pathlib import Path
from app.services.advanced_sort_service import SORT_OPTIONS, sort_candidates
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.4.1','VERSION 13.4.1')
    base=[
      {'name':'A','price':200,'offer_count':1,'relevance':70,'updated_at':'2026-01-01T00:00:00','raw_product_count':1,'offers':[{'price':200,'old_price':250}]},
      {'name':'B','price':100,'offer_count':4,'relevance':60,'updated_at':'2026-02-01T00:00:00','raw_product_count':3,'offers':[{'price':100,'old_price':100}]},
      {'name':'C','price':150,'offer_count':2,'relevance':90,'updated_at':'2026-03-01T00:00:00','raw_product_count':2,'offers':[{'price':150,'old_price':300}]},
    ]
    ok([x['name'] for x in sort_candidates(base,'price_asc')]==['B','C','A'],'fiyat artan sıralama doğru')
    ok([x['name'] for x in sort_candidates(base,'price_desc')]==['A','C','B'],'fiyat azalan sıralama doğru')
    ok(sort_candidates(base,'stores')[0]['name']=='B','mağaza sayısı sıralaması doğru')
    ok(sort_candidates(base,'price_drop')[0]['name']=='C','fiyat düşüş sıralaması doğru')
    ok(sort_candidates(base,'popular')[0]['name']=='B','popülerlik sıralaması doğru')
    ok(0 <= sort_candidates(base,'best_value')[0]['best_value_score'] <= 100,'fiyat performans puanı 0-100 aralığında')
    ok(sort_candidates(base,'newest')[0]['name']=='C','en yeni sıralaması doğru')
    ok({'price_drop','popular','best_value'}.issubset(SORT_OPTIONS),'gelişmiş sıralama seçenekleri mevcut')
    routes=(ROOT/'app/web/routes.py').read_text(encoding='utf-8')
    tpl=(ROOT/'app/templates/search_results.html').read_text(encoding='utf-8')
    ok('sort_candidates(candidates, selected_sort)' in routes,'/arama gelişmiş sıralama motoruna bağlı')
    ok('sort_options.items()' in tpl,'sıralama seçenekleri arayüzde dinamik')
    ok('price_drop_percent' in tpl,'fiyat düşüş rozeti mevcut')
    print('\nFırsatAI v13.4.1 Gelişmiş Sıralama smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
