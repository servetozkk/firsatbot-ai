from pathlib import Path
import sqlite3
import sys

def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("OK ", msg)

def main():
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.4.0", "VERSION 14.4.0")
    service = (root / "app/services/global_marketplace_v14_service.py").read_text(encoding="utf-8")
    routes = (root / "app/web/global_marketplace_v14_routes.py").read_text(encoding="utf-8")
    cat = (root / "app/templates/global_marketplace_catalog_v14.html").read_text(encoding="utf-8")
    detail = (root / "app/templates/global_marketplace_product_v14.html").read_text(encoding="utf-8")
    main_text = (root / "main.py").read_text(encoding="utf-8")
    ok("list_global_products" in service, "global ürün listeleme servisi mevcut")
    ok("get_global_product" in service, "tek ürün teklif toplama servisi mevcut")
    ok("/fiyat-karsilastirma" in routes, "fiyat karşılaştırma katalog route'u mevcut")
    ok("/api/global-marketplace/v14/products" in routes, "global marketplace API mevcut")
    ok("market-grid" in cat and "Fiyatları karşılaştır" in cat, "Akakçe tipi ürün kartları mevcut")
    ok("offer-list" in detail and "Mağazaya git" in detail, "mağaza teklif karşılaştırması mevcut")
    ok("global_marketplace_v14_router" in main_text, "global marketplace router uygulamaya bağlı")
    con = sqlite3.connect(root / "data/products.db")
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        ok("global_products" in tables, "global ürün tablosu mevcut")
        ok("bulk_catalog_items" in tables, "toplu katalog staging tablosu mevcut")
        ok("bulk_identity_links" in tables, "toplu kimlik bağlantıları mevcut")
        ok(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity başarılı")
        ok(len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0, "foreign key ihlali yok")
    finally:
        con.close()
    print("\nFırsatAI v14.4.0 Akakçe Tipi Global Fiyat Karşılaştırma smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
