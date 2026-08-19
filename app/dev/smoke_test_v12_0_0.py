from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print(f"OK  {m}")
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='12.0.0','VERSION 12.0.0')
    report=ROOT/'data/reports/v12_0_0_final_release_report.json'
    ok(report.exists(),'final release raporu oluşturuldu')
    d=json.loads(report.read_text(encoding='utf-8'))
    ok(d['database']['integrity']=='ok','SQLite integrity başarılı')
    ok(d['database']['foreign_key_violations']==0,'foreign key ihlali yok')
    ok(not d['performance']['missing_indexes'],'performans indeksleri tam')
    ok(not d['blockers'],'production engeli yok')
    ok(all(x['ok'] for x in d['regression']),'final regresyon testleri başarılı')
    ok(d['akakce_model']['global_product_catalog'],'global ürün kataloğu korunuyor')
    ok(d['akakce_model']['multi_store_offers'],'çok mağazalı teklif yapısı korunuyor')
    ok(d['status'] in {'PRODUCTION_READY','PRODUCTION_READY_FOR_DEPLOYMENT'},'final release durumu geçerli')
    print('\nFırsatAI v12.0.0 Production Final smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
