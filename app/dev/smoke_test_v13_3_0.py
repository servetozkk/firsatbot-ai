from pathlib import Path
from app.services.smart_search_service import parse_smart_query, enrich_and_rank_candidates

ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)

def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.3.0','VERSION 13.3.0')
    q=parse_smart_query('30 bin altı RTX 5060 32 GB RAM 1TB SSD oyuncu laptopu')
    ok(q['category']=='laptop','doğal dil kategori parser çalışıyor')
    ok(q['price_max']==30000,'fiyat üst sınırı ayrıştırılıyor')
    ok(q['gpu']=='RTX 5060','GPU ayrıştırılıyor')
    ok(q['ram_gb']==32,'RAM ayrıştırılıyor')
    ok(q['storage_gb']==1024,'1TB SSD ayrıştırılıyor')
    typo=parse_smart_query('samsng s25 telefon')
    ok(typo['brand']=='samsung','yazım hatası marka düzeltmesi çalışıyor')
    rows=[{'name':'RTX 5060 Gaming Laptop','brand':'X','category':'laptop','ram':'32gb','storage':'1024gb','price':29000,'offer_count':3,'attributes':{'gpu':'RTX 5060'},'relevance':10}]
    ranked=enrich_and_rank_candidates(rows,q)
    ok(bool(ranked) and ranked[0]['semantic_score']>60,'açıklanabilir semantic sıralama çalışıyor')
    ok(bool(ranked[0]['search_reasons']),'arama nedenleri üretiliyor')
    route=(ROOT/'app/web/smart_search_routes.py').read_text(encoding='utf-8')
    ok('/autocomplete-v13' in route and '/intelligence' in route,'akıllı arama API endpointleri mevcut')
    main_src=(ROOT/'main.py').read_text(encoding='utf-8')
    ok('smart_search_routes' in main_src,'akıllı arama router uygulamaya bağlı')
    routes=(ROOT/'app/web/routes.py').read_text(encoding='utf-8')
    ok('parse_smart_query' in routes and 'enrich_and_rank_candidates' in routes,'/arama semantic motorla entegre')
    tpl=(ROOT/'app/templates/search_results.html').read_text(encoding='utf-8')
    ok('smart-query-panel' in tpl,'açıklanabilir arama özeti arayüzde mevcut')
    print('\nFırsatAI v13.3.0 Akıllı Arama smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
