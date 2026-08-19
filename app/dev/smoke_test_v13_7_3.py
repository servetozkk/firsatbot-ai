from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from app.services.catalog_scaling_service import decode_cursor, encode_cursor, iter_products_ndjson, list_products_cursor

ROOT = Path(__file__).resolve().parents[2]


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def build_db(path: Path):
    with closing(sqlite3.connect(path)) as con:
        con.executescript("""
    CREATE TABLE global_products(id INTEGER PRIMARY KEY, identity_key TEXT, canonical_name TEXT, normalized_brand TEXT, category TEXT, primary_image TEXT, active_offer_count INTEGER, status TEXT, updated_at TEXT);
    CREATE TABLE global_offers(id INTEGER PRIMARY KEY, global_product_id INTEGER, store_code TEXT, current_price REAL, shipping_price REAL, is_active INTEGER, is_hidden INTEGER);
    CREATE INDEX ix_global_products_status_id ON global_products(status,id);
    CREATE INDEX ix_global_offers_product_active_price ON global_offers(global_product_id,is_active,is_hidden,current_price);
        """)
        for i in range(1, 7):
            con.execute("INSERT INTO global_products VALUES(?,?,?,?,?,?,?,?,?)", (i, f'k{i}', f'Ürün {i}', 'Marka', 'Laptop', '', 1, 'active', '2026-01-01'))
            con.execute("INSERT INTO global_offers VALUES(?,?,?,?,?,?,?)", (i, i, 'store', 1000+i, 0, 1, 0))
        con.commit()


def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version == '13.7.3', 'VERSION 13.7.3')
    token = encode_cursor(123)
    ok(decode_cursor(token) == 123, 'cursor güvenli kodlanıp çözülüyor')
    try:
        decode_cursor('%%%')
        raise AssertionError('geçersiz cursor reddedilmedi')
    except ValueError:
        print('OK  geçersiz cursor güvenli reddediliyor')
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'test.db'; build_db(db)
        first = list_products_cursor(limit=2, db_path=db)
        ok(first['count'] == 2 and first['has_more'], 'ilk keyset sayfası doğru')
        second = list_products_cursor(cursor=first['next_cursor'], limit=2, db_path=db)
        ok([x['id'] for x in second['items']] == [3,4], 'cursor sonraki sayfayı doğru getiriyor')
        ok(first['pagination'] == 'keyset', 'keyset pagination aktif')
        chunks = list(iter_products_ndjson(limit=2, db_path=db))
        ok(len(chunks) == 3 and json.loads(chunks[-1])['has_more'], 'streaming NDJSON yanıtı çalışıyor')
        with closing(sqlite3.connect(db)) as check_con:
            ok(check_con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'geçici SQLite bağlantıları güvenle kapanıyor')
    route = (ROOT / 'app/web/catalog_scaling_routes.py').read_text(encoding='utf-8')
    main_text = (ROOT / 'main.py').read_text(encoding='utf-8')
    ok('/api/products/v13' in route, 'cursor ürün API endpoint mevcut')
    ok('/api/products/v13/stream' in route, 'streaming endpoint mevcut')
    ok('/api/catalog-health/v13' in route, 'catalog health API mevcut')
    ok('catalog_scaling_router' in main_text, 'catalog scaling router uygulamaya bağlı')
    print('\nFırsatAI v13.7.3 Büyük Katalog Ölçekleme smoke test başarılı.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
