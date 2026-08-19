from pathlib import Path
import json, sqlite3
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
 if not v: raise AssertionError(m)
 print('OK ',m)
def main():
 ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.2.6','VERSION 11.2.6')
 p=ROOT/'data/reports/v11_2_6_manual_decision_execute.json'; ok(p.exists(),'karar uygulama raporu oluşturuldu')
 d=json.loads(p.read_text(encoding='utf-8')); ok(d['merged_group_count']==8,'8 güvenli eski grup birleştirildi'); ok(not d['remaining_source_groups'],'kaynak gruplar kalmadı')
 con=sqlite3.connect(ROOT/'data/products.db')
 for gid in [53,56,59,60,61,70,71,78]: ok(con.execute('select count(*) from product_groups where id=?',(gid,)).fetchone()[0]==0,f'kaynak grup {gid} silindi')
 ok(con.execute('select count(*) from product_groups').fetchone()[0]==129,'grup sayısı 129')
 con.close(); print('\nFırsatAI v11.2.6 smoke test başarılı.'); return 0
if __name__=='__main__': raise SystemExit(main())
