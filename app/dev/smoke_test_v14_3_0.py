from pathlib import Path
import sqlite3, tempfile

def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)

def main():
    root=Path(__file__).resolve().parents[2]
    ok((root/'VERSION').read_text(encoding='utf-8').strip()=='14.3.0','VERSION 14.3.0')
    service=(root/'app/services/bulk_identity_service.py').read_text(encoding='utf-8')
    routes=(root/'app/web/admin_bulk_identity_routes.py').read_text(encoding='utf-8')
    main_text=(root/'main.py').read_text(encoding='utf-8')
    ok('bulk_identity_links' in service,'staging-global ürün bağlantı tablosu mevcut')
    ok('bulk_identity_decisions' in service,'kimlik karar geçmişi mevcut')
    ok('ProductIdentityService.explain' in service,'mevcut kimlik motoru toplu akışa bağlı')
    ok('identity_key' in service and 'global_products' in service,'deterministik global ürün upsert mevcut')
    ok('global_product_variants' in service,'varyant upsert mevcut')
    ok("cross" not in service.lower() or 'mağazada çapraz arama yapmaz' in service,'toplu eşleştirme çapraz mağaza araması yapmıyor')
    ok('/api/bulk-identity/v14/process' in routes,'toplu eşleştirme API mevcut')
    ok('/admin/bulk-identity' in routes,'toplu kimlik yönetim paneli mevcut')
    ok('bulk_identity_router' in main_text,'toplu kimlik router uygulamaya bağlı')
    db=root/'data/products.db'
    if db.exists():
        con=sqlite3.connect(db)
        ok(con.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity başarılı')
        ok(len(con.execute('PRAGMA foreign_key_check').fetchall())==0,'foreign key ihlali yok')
        con.close()
    print('\nFırsatAI v14.3.0 Toplu Kimlik ve Global Ürün Motoru smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
