from __future__ import annotations

import argparse, json, os, shutil, sqlite3, statistics, tempfile, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / 'data' / 'products.db'
REPORT = ROOT / 'data' / 'reports' / 'v11_5_0_performance_scale_report.json'
BACKUP_DIR = ROOT / 'data' / 'backups' / 'performance_v11_5_0'

INDEXES = {
    'ix_product_offers_group_active_hidden_price':
        'CREATE INDEX IF NOT EXISTS ix_product_offers_group_active_hidden_price ON product_offers(group_id, is_active, is_hidden, current_price)',
    'ix_product_offers_store_active_checked':
        'CREATE INDEX IF NOT EXISTS ix_product_offers_store_active_checked ON product_offers(store_id, is_active, last_checked_at)',
    'ix_offer_price_history_offer_created':
        'CREATE INDEX IF NOT EXISTS ix_offer_price_history_offer_created ON offer_price_history(offer_id, created_at)',
    'ix_product_groups_category_brand':
        'CREATE INDEX IF NOT EXISTS ix_product_groups_category_brand ON product_groups(category, brand)',
}

QUERIES = {
    'global_product_offers': '''SELECT id, store_id, current_price, availability
        FROM product_offers
        WHERE group_id=? AND is_active=1 AND is_hidden=0
        ORDER BY current_price ASC LIMIT 50''',
    'offer_price_history': '''SELECT price, created_at FROM offer_price_history
        WHERE offer_id=? ORDER BY created_at DESC LIMIT 365''',
    'store_fresh_offers': '''SELECT id, group_id, current_price FROM product_offers
        WHERE store_id=? AND is_active=1 ORDER BY last_checked_at DESC LIMIT 100''',
    'category_brand_groups': '''SELECT id, canonical_name FROM product_groups
        WHERE category=? AND brand=? ORDER BY updated_at DESC LIMIT 100''',
}

def ms_benchmark(conn, sql, params, rounds=250):
    values=[]
    for _ in range(rounds):
        t=time.perf_counter_ns(); conn.execute(sql, params).fetchall(); values.append((time.perf_counter_ns()-t)/1e6)
    values.sort()
    return {'median_ms': round(statistics.median(values),4), 'p95_ms': round(values[int(len(values)*.95)-1],4), 'max_ms': round(max(values),4)}

def pick_params(conn):
    group=conn.execute('SELECT group_id FROM product_offers GROUP BY group_id ORDER BY COUNT(*) DESC LIMIT 1').fetchone()
    offer=conn.execute('SELECT offer_id FROM offer_price_history GROUP BY offer_id ORDER BY COUNT(*) DESC LIMIT 1').fetchone()
    store=conn.execute('SELECT store_id FROM product_offers GROUP BY store_id ORDER BY COUNT(*) DESC LIMIT 1').fetchone()
    cb=conn.execute("SELECT category, brand FROM product_groups WHERE category IS NOT NULL AND brand IS NOT NULL LIMIT 1").fetchone()
    return {
      'global_product_offers': (group[0] if group else -1,),
      'offer_price_history': (offer[0] if offer else -1,),
      'store_fresh_offers': (store[0] if store else -1,),
      'category_brand_groups': tuple(cb) if cb else ('__none__','__none__'),
    }

def explain(conn, sql, params):
    return [r[3] for r in conn.execute('EXPLAIN QUERY PLAN '+sql, params).fetchall()]

def synthetic_test(rows=100000):
    tmp_dir = ROOT / 'data' / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / f'v11_5_0_scale_{os.getpid()}_{int(time.time() * 1000)}.db'
    c = None
    try:
        c = sqlite3.connect(str(db_path))
        c.executescript('''
          PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
          CREATE TABLE product_offers(id INTEGER PRIMARY KEY, group_id INTEGER, store_id INTEGER, current_price REAL, availability TEXT, is_active INTEGER, is_hidden INTEGER, last_checked_at TEXT);
          CREATE TABLE offer_price_history(id INTEGER PRIMARY KEY, offer_id INTEGER, price REAL, created_at TEXT);
        ''')
        batch=[]
        now='2026-08-02 00:00:00'
        for i in range(rows):
            batch.append((i%20000+1, i%10+1, float(100+(i%50000)), 'IN_STOCK', 1, 0, now))
        c.executemany('INSERT INTO product_offers(group_id,store_id,current_price,availability,is_active,is_hidden,last_checked_at) VALUES(?,?,?,?,?,?,?)', batch)
        hist=[(i%max(1,rows//10)+1, float(100+(i%10000)), now) for i in range(rows)]
        c.executemany('INSERT INTO offer_price_history(offer_id,price,created_at) VALUES(?,?,?)', hist); c.commit()
        q1=QUERIES['global_product_offers']; q2=QUERIES['offer_price_history']
        before={'offers':ms_benchmark(c,q1,(1,),80),'history':ms_benchmark(c,q2,(1,),80)}
        c.execute(INDEXES['ix_product_offers_group_active_hidden_price']); c.execute(INDEXES['ix_offer_price_history_offer_created']); c.commit()
        after={'offers':ms_benchmark(c,q1,(1,),80),'history':ms_benchmark(c,q2,(1,),80)}
        return {'rows_per_table':rows,'before':before,'after':after,'temp_db':str(db_path)}
    finally:
        if c is not None:
            c.close()
        for suffix in ('', '-wal', '-shm', '-journal'):
            try:
                Path(str(db_path) + suffix).unlink(missing_ok=True)
            except OSError:
                pass

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--apply-indexes',action='store_true'); ap.add_argument('--synthetic-rows',type=int,default=100000); args=ap.parse_args()
    if not DB.exists(): raise SystemExit(f'Veritabanı bulunamadı: {DB}')
    REPORT.parent.mkdir(parents=True, exist_ok=True); BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(DB); conn.execute('PRAGMA foreign_keys=ON')
    integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
    fk=len(conn.execute('PRAGMA foreign_key_check').fetchall())
    params=pick_params(conn)
    before={k:ms_benchmark(conn,q,params[k]) for k,q in QUERIES.items()}
    plans_before={k:explain(conn,q,params[k]) for k,q in QUERIES.items()}
    existing={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    missing=[k for k in INDEXES if k not in existing]
    backup=None
    if args.apply_indexes and missing:
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); backup=BACKUP_DIR/f'products_before_indexes_{stamp}.db'
        dst=sqlite3.connect(backup); conn.backup(dst); dst.close()
        for name in missing: conn.execute(INDEXES[name])
        conn.commit(); conn.execute('ANALYZE'); conn.commit()
    after={k:ms_benchmark(conn,q,params[k]) for k,q in QUERIES.items()}
    plans_after={k:explain(conn,q,params[k]) for k,q in QUERIES.items()}
    counts={t:conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('product_groups','product_offers','offer_price_history','stores')}
    installed=[k for k in INDEXES if k in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}]
    conn.close()
    synth=synthetic_test(max(10000,args.synthetic_rows))
    improvements={}
    for k in QUERIES:
        b=before[k]['median_ms']; a=after[k]['median_ms']; improvements[k]=round(((b-a)/b*100),2) if b else 0
    status='PERFORMANCE_READY' if integrity=='ok' and fk==0 and len(installed)==len(INDEXES) else 'PERFORMANCE_READY_WITH_WARNINGS'
    out={'version':'11.5.0','read_only':False,'status':status,'integrity':integrity,'foreign_key_violations':fk,'counts':counts,'missing_before':missing,'installed_indexes':installed,'backup':str(backup) if backup else None,'benchmarks_before':before,'benchmarks_after':after,'improvement_percent':improvements,'query_plans_before':plans_before,'query_plans_after':plans_after,'synthetic_scale':synth,'generated_at':datetime.now().isoformat()}
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OK  Product Group: {counts['product_groups']}"); print(f"OK  Teklif: {counts['product_offers']}"); print(f"OK  Fiyat geçmişi: {counts['offer_price_history']}")
    print(f"OK  SQLite integrity: {integrity}"); print(f"OK  Foreign key ihlali: {fk}")
    print(f"OK  Kurulan performans indeksi: {len(installed)}/{len(INDEXES)}")
    for k,v in after.items(): print(f"BİLGİ  {k}: median={v['median_ms']} ms, p95={v['p95_ms']} ms")
    print(f"BİLGİ  Sentetik ölçek testi: {synth['rows_per_table']} satır/tablo")
    print(f"DURUM: {status}"); print(f"RAPOR: {REPORT}")
    if backup: print(f"DB YEDEĞİ: {backup}")
    return 0
if __name__=='__main__': raise SystemExit(main())
