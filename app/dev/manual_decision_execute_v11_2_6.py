from __future__ import annotations
import json, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DB=ROOT/'data'/'products.db'
REPORT_DIR=ROOT/'data'/'reports'; BACKUP_DIR=ROOT/'data'/'backups'/'manual_decisions'
REPORT=REPORT_DIR/'v11_2_6_manual_decision_execute.json'
REGISTRY=REPORT_DIR/'v11_2_6_review_decisions.json'
VERSION='11.2.6'

# İnsan incelemesiyle doğrulanan kararlar.
MOVE_DECISIONS=[
 {'offer_id':35,'decision':'AYRI_TUT','reason':'Mevcut grup skoru daha yüksek; aynı adlı ayrı katalog kaydı körlemesine taşınmamalı.'},
 {'offer_id':76,'decision':'AYRI_TUT','reason':'Galaxy A26 ile Galaxy S26 farklı model.'},
 {'offer_id':78,'decision':'AYRI_TUT','reason':'Depolaması bilinmeyen iPhone 15, 128 GB varyantına varsayımla taşınamaz.'},
 {'offer_id':89,'decision':'AYRI_TUT','reason':'13-14 inç çanta ile 15-15,9 inç çanta farklı varyant.'},
 {'offer_id':90,'decision':'AYRI_TUT','reason':'15-15,9 inç çanta ile 13-14 inç çanta farklı varyant.'},
 {'offer_id':94,'decision':'AYRI_TUT','reason':'Galaxy A16 ile Galaxy A17 farklı model ve kapasite.'},
]
# Kaynak gruplar teklifsiz eski kimlik kayıtlarıdır; hedefler aktif V2 gruplarıdır.
MERGE_PAIRS=[(53,141),(56,155),(59,142),(60,143),(61,144),(70,156),(71,154),(78,125)]
DEFERRED_MERGES=[
 {'groups':[80,121],'decision':'AYRI_TUT','reason':'iPhone 17 renk ve RAM metadata farkı; renk varyant politikası netleşmeden birleştirilmez.'},
 {'groups':[76,106],'decision':'AYRI_TUT','reason':'iPhone 17 Pro renk adları farklı; renk varyant politikası netleşmeden birleştirilmez.'},
]

def rowdict(r): return dict(r) if r else None

def eq_spec(a,b):
 return (a['value_text'],a['value_number'],a['value_boolean'])==(b['value_text'],b['value_number'],b['value_boolean'])

def merge_pair(con, source:int, target:int):
 sg=con.execute('select * from product_groups where id=?',(source,)).fetchone(); tg=con.execute('select * from product_groups where id=?',(target,)).fetchone()
 if not sg or not tg: raise RuntimeError(f'Grup bulunamadı: {source}->{target}')
 so=con.execute('select count(*) from product_offers where group_id=?',(source,)).fetchone()[0]
 to=con.execute('select count(*) from product_offers where group_id=?',(target,)).fetchone()[0]
 if so!=0 or to<1: raise RuntimeError(f'Güvenlik koşulu bozuldu {source}->{target}: kaynak_teklif={so}, hedef_teklif={to}')
 moved={}; duplicates={}
 # Specification: aynı feature aynı değerse kaynak kopyayı sil, farklıysa tüm transaction durur.
 src=list(con.execute('select * from product_feature_values where product_group_id=? order by id',(source,)))
 for r in src:
  t=con.execute('select * from product_feature_values where product_group_id=? and feature_id=?',(target,r['feature_id'])).fetchone()
  if not t:
   con.execute('update product_feature_values set product_group_id=? where id=?',(target,r['id'])); moved['product_feature_values']=moved.get('product_feature_values',0)+1
  elif eq_spec(r,t):
   con.execute('delete from product_feature_values where id=?',(r['id'],)); duplicates['product_feature_values']=duplicates.get('product_feature_values',0)+1
  else:
   raise RuntimeError(f'Specification çakışması {source}->{target}, feature_id={r["feature_id"]}')
 # Kullanıcı ilişkileri: hedefte aynı benzersiz anahtar varsa eski kopyayı kaldır.
 rules=[('favorites','visitor_id'),('price_alerts','visitor_id'),('recently_viewed','user_id'),('product_reviews','user_id')]
 for table,key in rules:
  rows=list(con.execute(f'select * from {table} where product_group_id=?',(source,)))
  for r in rows:
   exists=con.execute(f'select id from {table} where product_group_id=? and {key}=?',(target,r[key])).fetchone()
   if exists:
    con.execute(f'delete from {table} where id=?',(r['id'],)); duplicates[table]=duplicates.get(table,0)+1
   else:
    con.execute(f'update {table} set product_group_id=? where id=?',(target,r['id'])); moved[table]=moved.get(table,0)+1
 # Tüm FK referansları sıfır olmalı.
 refs=[]
 for table,col in [('product_offers','group_id'),('product_feature_values','product_group_id'),('favorites','product_group_id'),('price_alerts','product_group_id'),('recently_viewed','product_group_id'),('product_reviews','product_group_id')]:
  n=con.execute(f'select count(*) from {table} where {col}=?',(source,)).fetchone()[0]
  if n: refs.append({'table':table,'count':n})
 if refs: raise RuntimeError(f'Kaynak grupta referans kaldı {source}: {refs}')
 con.execute('delete from product_groups where id=?',(source,))
 return {'source_group_id':source,'target_group_id':target,'moved':moved,'duplicates_removed':duplicates,'source_name':sg['canonical_name'],'target_name':tg['canonical_name']}

def main():
 if not DB.exists(): raise FileNotFoundError(DB)
 REPORT_DIR.mkdir(parents=True,exist_ok=True); BACKUP_DIR.mkdir(parents=True,exist_ok=True)
 stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
 db_backup=BACKUP_DIR/f'products_before_v11_2_6_{stamp}.db'
 # SQLite backup API, WAL dahil tutarlı kopya üretir.
 src=sqlite3.connect(DB); dst=sqlite3.connect(db_backup); src.backup(dst); dst.close(); src.close()
 con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; con.execute('pragma foreign_keys=on')
 before=con.execute('select count(*) from product_groups').fetchone()[0]
 results=[]
 try:
  con.execute('begin immediate')
  for s,t in MERGE_PAIRS: results.append(merge_pair(con,s,t))
  con.commit()
 except Exception:
  con.rollback(); con.close(); raise
 after=con.execute('select count(*) from product_groups').fetchone()[0]
 remaining_sources=[s for s,_ in MERGE_PAIRS if con.execute('select 1 from product_groups where id=?',(s,)).fetchone()]
 con.close()
 registry={'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'move_decisions':MOVE_DECISIONS,'executed_merges':results,'deferred_merges':DEFERRED_MERGES}
 REGISTRY.write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'version':VERSION,'mode':'reviewed_decision_executor','group_count_before':before,'group_count_after':after,'merged_group_count':len(results),'remaining_source_groups':remaining_sources,'move_decisions_recorded':len(MOVE_DECISIONS),'deferred_merge_decisions':len(DEFERRED_MERGES),'database_backup':str(db_backup),'merges':results}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'OK  Uygulanan güvenli grup birleştirmesi: {len(results)}')
 print(f'OK  Ayrı tutulan taşıma adayı: {len(MOVE_DECISIONS)}')
 print(f'OK  Ertelenen renk varyantı birleştirmesi: {len(DEFERRED_MERGES)}')
 print(f'OK  Grup sayısı: {before} -> {after}')
 print(f'OK  Kalan kaynak grup: {len(remaining_sources)}')
 print(f'YEDEK: {db_backup}')
 print(f'KARAR KAYDI: {REGISTRY}')
 print(f'RAPOR: {REPORT}')
 return 0
if __name__=='__main__': raise SystemExit(main())
