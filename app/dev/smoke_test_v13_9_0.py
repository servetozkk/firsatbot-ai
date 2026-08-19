from __future__ import annotations
import os, sqlite3, tempfile
from pathlib import Path

def ok(value, message):
    if not value: raise AssertionError(message)
    print("OK ", message)

def main():
    root=Path(__file__).resolve().parents[2]
    ok((root/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.9.0','VERSION 13.9.0')
    with tempfile.TemporaryDirectory() as td:
        os.environ['FIRSATAI_PUBLIC_BETA_DB_PATH']=str(Path(td)/'test.db')
        from app.services.public_beta_service import ensure_schema, submit_feedback, statistics, public_beta_status
        ensure_schema()
        row=submit_feedback(feedback_type='bug',message='Karşılaştırma ekranında örnek bir beta hatası var.',page_path='/karsilastir')
        ok(row['status']=='new','anonim geri bildirim oluşturuluyor')
        stats=statistics(30)
        ok(stats['feedback_total']==1,'geri bildirim istatistiği üretiliyor')
        conn=sqlite3.connect(os.environ['FIRSATAI_PUBLIC_BETA_DB_PATH'])
        try:
            cols={r[1] for r in conn.execute('PRAGMA table_info(public_beta_feedback)').fetchall()}
            ok('email' not in cols and 'ip_address' not in cols and 'user_id' not in cols,'kişisel veri alanı oluşturulmuyor')
        finally: conn.close()
    route=(root/'app/web/public_beta_routes.py').read_text(encoding='utf-8')
    main_text=(root/'main.py').read_text(encoding='utf-8',errors='ignore')
    base=(root/'app/templates/public_base.html').read_text(encoding='utf-8',errors='ignore')
    ok('/api/public-beta/status' in route,'Public Beta durum API mevcut')
    ok('/api/public-beta/feedback' in route,'Feedback API mevcut')
    ok('/admin/public-beta' in route,'Public Beta dashboard mevcut')
    ok('public_beta_router' in main_text and 'app.include_router(public_beta_router)' in main_text,'Public Beta router uygulamaya bağlı')
    ok('public-beta-banner' in base and '/geri-bildirim' in base,'Public Beta banner ve geri bildirim bağlantısı mevcut')
    ok('FırsatAI Public Beta' in base and '13.9.0' in base,'footer Public Beta sürümünü gösteriyor')
    db=root/'data/products.db'
    if db.exists():
        c=sqlite3.connect(str(db))
        try:
            ok(c.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity başarılı')
            ok(len(c.execute('PRAGMA foreign_key_check').fetchall())==0,'foreign key ihlali yok')
        finally:c.close()
    print('\nFırsatAI v13.9.0 Public Beta smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
