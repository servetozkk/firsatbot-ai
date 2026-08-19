from __future__ import annotations
import json, sqlite3, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app.services.smart_search_service import parse_smart_query, enrich_and_rank_candidates, build_autocomplete, normalize_text

DB=ROOT/'data'/'products.db'
REPORT=ROOT/'data'/'reports'/'v13_3_1_smart_search_real_data_acceptance.json'

def ok(v,msg,checks):
    if not v: raise AssertionError(msg)
    print('OK ',msg); checks.append(msg)

def candidates(conn):
    rows=conn.execute('''
      SELECT p.id,p.identity_key,p.canonical_name,p.normalized_brand,p.category,p.ram_gb,p.storage_gb,
             MIN(o.current_price+COALESCE(o.shipping_price,0)) price,
             COUNT(DISTINCT o.store_code) offer_count
      FROM global_products p JOIN global_offers o ON o.global_product_id=p.id
      WHERE p.status='ACTIVE' AND o.is_active=1 AND o.is_hidden=0 AND o.lifecycle_status='ACTIVE' AND o.current_price>0
      GROUP BY p.id
    ''').fetchall()
    out=[]
    for r in rows:
        name=r['canonical_name'] or ''
        out.append({'id':r['id'],'identity_key':r['identity_key'],'name':name,'brand':r['normalized_brand'] or '',
          'model':name,'category':r['category'] or name,'ram':f"{r['ram_gb']}gb" if r['ram_gb'] is not None else '',
          'storage':f"{r['storage_gb']}gb" if r['storage_gb'] is not None else '', 'price':float(r['price'] or 0),
          'offer_count':int(r['offer_count'] or 0),'relevance':1,'url':f"/urun/{r['identity_key']}",'attributes':{}})
    return out

def _capacity(value):
    import re
    m=re.search(r'(\d+(?:\.\d+)?)', str(value or ''))
    return int(float(m.group(1))) if m else None

def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip(); checks=[]
    ok(version=='13.3.1','VERSION 13.3.1',checks)
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    ok(conn.execute('pragma integrity_check').fetchone()[0]=='ok','SQLite integrity_check başarılı',checks)
    ok(len(conn.execute('pragma foreign_key_check').fetchall())==0,'foreign key ihlali yok',checks)
    items=candidates(conn); ok(len(items)>0,'aktif gerçek katalog adayları mevcut',checks)

    typo=parse_smart_query('samsng s25 telefon')
    ok(typo['brand']=='samsung','yazım hatalı Samsung sorgusu normalize ediliyor',checks)
    typo_rank=enrich_and_rank_candidates(items,typo)
    ok(len(typo_rank)>0,'yazım hatalı sorgu gerçek sonuç üretiyor',checks)
    ok('samsung' in normalize_text(typo_rank[0].get('brand') or typo_rank[0].get('name')),'yazım hatalı sorguda Samsung üst sırada',checks)

    budget=parse_smart_query('30 bin altı laptop')
    budget_rank=enrich_and_rank_candidates(items,budget)
    ok(len(budget_rank)>0,'fiyat üst sınırı gerçek sonuç üretiyor',checks)
    ok(all(float(x['price'])<=30000 for x in budget_rank),'30 bin fiyat üst sınırı uygulanıyor',checks)
    ok(all('laptop' in normalize_text(x.get('category')) or 'laptop' in normalize_text(x.get('name')) for x in budget_rank),'yanlış kategori ürünleri eleniyor',checks)

    tech=parse_smart_query('16 GB RAM 512 GB SSD laptop')
    tech_rank=enrich_and_rank_candidates(items,tech)
    ok(len(tech_rank)>0,'RAM ve depolama sorgusu gerçek sonuç üretiyor',checks)
    ok(all(_capacity(x.get('ram'))==16 and _capacity(x.get('storage'))==512 for x in tech_rank),'RAM ve depolama filtreleri uygulanıyor',checks)
    ok(all(x.get('search_reasons') for x in tech_rank),'açıklanabilir arama nedenleri üretiliyor',checks)
    ok(all(0<=int(x.get('semantic_score',-1))<=100 for x in tech_rank),'semantic skorlar 0-100 aralığında',checks)
    ok(all(float(tech_rank[i].get('relevance',0))>=float(tech_rank[i+1].get('relevance',0)) for i in range(len(tech_rank)-1)),'sonuç sırası semantic skorla tutarlı',checks)

    # Katalogda gerçekten bulunan bir GPU + kategori kombinasyonunu seç.
    # Sabit RTX 5060 laptop sorgusu, katalogda RTX 5060 yalnızca masaüstünde
    # varsa doğru olarak boş döner ve motor sağlam olsa bile testi yanıltır.
    import re
    gpu_pattern=re.compile(r"\b(?:rtx\s*\d{4}(?:\s*ti|\s*super)?|gtx\s*\d{3,4}(?:\s*ti)?|rx\s*\d{4}(?:\s*xt)?)\b",re.I)
    gpu_case=None
    for row in items:
        match=gpu_pattern.search(str(row.get('name') or ''))
        if not match:
            continue
        category='laptop' if 'laptop' in normalize_text(row.get('category')) or 'laptop' in normalize_text(row.get('name')) else None
        if category:
            gpu_case=(re.sub(r"\s+"," ",match.group(0)).upper(),category)
            break
    if gpu_case is None:
        for row in items:
            match=gpu_pattern.search(str(row.get('name') or ''))
            if match:
                gpu_case=(re.sub(r"\s+"," ",match.group(0)).upper(),None)
                break
    ok(gpu_case is not None,'katalogda GPU içeren gerçek ürün mevcut',checks)
    gpu_name,gpu_category=gpu_case
    gpu_query=f"{gpu_name} {gpu_category or ''}".strip()
    gpu=parse_smart_query(gpu_query)
    gpu_rank=enrich_and_rank_candidates(items,gpu)
    ok(len(gpu_rank)>0,f'GPU sorgusu gerçek sonuç üretiyor ({gpu_query})',checks)
    compact_gpu=re.sub(r"[^a-z0-9]+","",normalize_text(gpu_name))
    ok(all(compact_gpu in re.sub(r"[^a-z0-9]+","",normalize_text(x.get('name'))) for x in gpu_rank),'GPU şartı gerçek ürünlerde uygulanıyor',checks)

    none=parse_smart_query('128 GB RAM 4096 GB SSD telefon')
    none_rank=enrich_and_rank_candidates(items,none)
    ok(len(none_rank)==0,'sonuçsuz sorgu güvenli boş sonuç üretiyor',checks)

    auto_source=typo_rank or items
    auto_query=str(auto_source[0].get('name') or '')
    auto=build_autocomplete(auto_query,items)
    ok(isinstance(auto,list),'otomatik tamamlama liste üretiyor',checks)
    ok(any((r.get('url') or '').startswith('/urun/') for r in auto if r.get('type')=='product'),'otomatik tamamlama gerçek global ürün URL üretiyor',checks)

    report={'version':version,'read_only':True,'status':'SMART_SEARCH_REAL_DATA_ACCEPTANCE_READY',
      'summary':{'catalog_candidates':len(items),'typo_results':len(typo_rank),'budget_results':len(budget_rank),
      'technical_results':len(tech_rank),'gpu_results':len(gpu_rank),'autocomplete_items':len(auto),
      'checks_passed':len(checks),'checks_total':len(checks)},'checks':checks}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RAPOR:',REPORT); print('DURUM: SMART_SEARCH_REAL_DATA_ACCEPTANCE_READY')
    return 0
if __name__=='__main__': raise SystemExit(main())
