from pathlib import Path
from app.services.comparison_v2_service import build_comparison_matrix, build_product_metrics, normalize_selected_keys, MAX_PRODUCTS
ROOT = Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.4.5','VERSION 13.4.5')
    ok(normalize_selected_keys(['a','b','a','c','d','e'])==['a','b','c','d'],'en fazla 4 benzersiz ürün destekleniyor')
    fm=[{'x':{'name':'RAM','section':'Bellek','sort_order':1,'display_value':'16 GB','raw_value':16,'comparison_type':'higher_better'}},{'x':{'name':'RAM','section':'Bellek','sort_order':1,'display_value':'32 GB','raw_value':32,'comparison_type':'higher_better'}},{'x':{'name':'RAM','section':'Bellek','sort_order':1,'display_value':'24 GB','raw_value':24,'comparison_type':'higher_better'}}]
    sections=build_comparison_matrix(fm)
    ok(sections[0]['rows'][0]['winner_indexes']==[1],'çoklu teknik özellik kazananı doğru')
    class P: pass
    ps=[]
    for i in range(3):
        p=P(); p.group_key=str(i); ps.append(p)
    metrics=build_product_metrics(ps,[{'best_price':100,'store_count':2},{'best_price':120,'store_count':4},{'best_price':110,'store_count':3}],sections)
    ok(all(0<=x['value_score']<=100 for x in metrics),'değer puanı 0-100 aralığında')
    route=(ROOT/'app/web/product_group_routes.py').read_text(encoding='utf-8-sig')
    tpl=(ROOT/'app/templates/product_group_compare_v2.html').read_text(encoding='utf-8-sig')
    ok('products: list[str]' in route and 'product_group_compare_v2.html' in route,'route 2-4 ürün akışına bağlı')
    ok('name="products"' in tpl and 'range(max_products)' in tpl,'arayüz 4 ürün seçimini destekliyor')
    ok('Yalnızca farklılar' in tpl and 'Bağlantıyı kopyala' in tpl,'fark filtresi ve paylaşılabilir URL mevcut')
    ok('@media(max-width:768px)' in tpl and 'compare-scroll' in tpl,'mobil yatay karşılaştırma mevcut')
    print('\nFırsatAI v13.4.5 Karşılaştırma 2.0 smoke test başarılı.')
if __name__=='__main__': raise SystemExit(main())
