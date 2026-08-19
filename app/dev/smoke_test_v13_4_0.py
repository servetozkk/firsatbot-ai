from pathlib import Path
import sqlite3
from app.services.advanced_filter_service import build_dynamic_facets, apply_dynamic_filters, filter_metadata
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8-sig').strip(); ok(version=='13.4.0','VERSION 13.4.0')
    sample=[{'category':'Laptop','attributes':{'gpu':'RTX 4060','panel':'IPS','refresh_rate':'165 Hz'}},{'category':'Laptop','attributes':{'gpu':'RTX 5060','panel':'OLED','refresh_rate':'240 Hz'}}]
    facets=build_dynamic_facets(sample,['Laptop']); keys={x['key'] for x in facets}
    ok({'gpu','panel','refresh_rate'}<=keys,'kategoriye duyarlı filtre sayaçları üretiliyor')
    filtered=apply_dynamic_filters(sample,{'gpu':['RTX 5060'],'panel':['OLED']}); ok(len(filtered)==1,'çoklu dinamik filtre birlikte uygulanıyor')
    meta=filter_metadata(['Laptop']); ok(meta['engine_version']=='13.4.0','filtre metadata API sürümü doğru')
    routes=(ROOT/'app/web/routes.py').read_text(encoding='utf-8'); tpl=(ROOT/'app/templates/search_results.html').read_text(encoding='utf-8')
    ok('/api/filters/v13' in routes,'filtre metadata endpoint mevcut')
    ok('getlist("brand")' in routes and 'getlist("store")' in routes,'çoklu marka ve mağaza filtresi korunuyor')
    ok('min_price' in routes and 'max_price' in routes,'fiyat aralığı filtresi mevcut')
    ok('mobileFilterButton' in tpl and 'filter-panel' in tpl,'mobil filtre deneyimi mevcut')
    ok('data-remove-name' in tpl,'aktif filtre kaldırma ve temizleme mevcut')
    db=ROOT/'data/products.db'; c=sqlite3.connect(db); ok(c.execute('pragma integrity_check').fetchone()[0]=='ok','SQLite integrity_check başarılı'); ok(len(c.execute('pragma foreign_key_check').fetchall())==0,'foreign key ihlali yok'); c.close()
    print('\nFırsatAI v13.4.0 Gelişmiş Filtreleme smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
