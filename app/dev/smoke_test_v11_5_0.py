from pathlib import Path
import json, sqlite3
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='11.5.0','VERSION 11.5.0')
    report=ROOT/'data/reports/v11_5_0_performance_scale_report.json'; ok(report.exists(),'performans raporu oluşturuldu')
    d=json.loads(report.read_text(encoding='utf-8')); ok(d['integrity']=='ok','SQLite integrity başarılı'); ok(d['foreign_key_violations']==0,'foreign key ihlali yok'); ok(len(d['installed_indexes'])==4,'4 bileşik indeks kuruldu'); ok(d['synthetic_scale']['rows_per_table']>=100000,'100 bin satırlık sentetik test çalıştı')
    c=sqlite3.connect(ROOT/'data/products.db'); names={r[0] for r in c.execute("select name from sqlite_master where type='index'")}; c.close()
    for n in ('ix_product_offers_group_active_hidden_price','ix_product_offers_store_active_checked','ix_offer_price_history_offer_created','ix_product_groups_category_brand'): ok(n in names,f'{n} mevcut')
    print('\nFırsatAI v11.5.0 Performans ve Ölçek smoke test başarılı.'); return 0
if __name__=='__main__': raise SystemExit(main())
