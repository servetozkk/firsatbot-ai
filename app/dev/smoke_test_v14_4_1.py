from pathlib import Path
import sqlite3

from app.services.global_marketplace_v14_service import get_global_product, list_global_products


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("OK ", msg)


def main():
    root = Path.cwd()
    ok((root / "VERSION").read_text(encoding="utf-8").strip() == "14.4.1", "VERSION 14.4.1")
    result = list_global_products(limit=12)
    ok(result["pagination"]["total"] > 0, "global ürün kataloğu fiyatlı ürün döndürüyor")
    ok(len(result["items"]) > 0, "global ürün kartları oluşturuluyor")
    first = result["items"][0]
    detail = get_global_product(first["id"])
    ok(detail is not None, "global ürün detay servisi çalışıyor")
    ok(detail["offer_count"] > 0, "global ürün mağaza teklifleri mevcut")
    con = sqlite3.connect(root / "data/products.db")
    try:
        ok(con.execute("SELECT COUNT(*) FROM global_offers WHERE is_active=1 AND is_hidden=0 AND current_price>0").fetchone()[0] > 0, "global_offers veri kaynağı dolu")
        ok(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity başarılı")
        ok(len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0, "foreign key ihlali yok")
    finally:
        con.close()
    print(f"\nBILGI  Fiyatlı global ürün: {result['pagination']['total']}")
    print(f"BILGI  Örnek ürün teklif sayısı: {detail['offer_count']}")
    print("\nFırsatAI v14.4.1 Global Teklif Veri Köprüsü smoke test başarılı.")


if __name__ == "__main__":
    main()
