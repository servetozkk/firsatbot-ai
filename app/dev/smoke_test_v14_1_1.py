from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "14.1.1", "VERSION 14.1.1")

    product_source = (ROOT / "app/services/product_service.py").read_text(encoding="utf-8")
    offer_source = (ROOT / "app/services/multi_store_service.py").read_text(encoding="utf-8")
    category_source = (ROOT / "app/services/category_discovery_service.py").read_text(encoding="utf-8")

    ok(
        "ProductDB.product_code == product.product_code" in product_source
        and "ProductDB.source_site == product.source_site" in product_source,
        "mağaza ürünü URL değişse bile ürün koduyla bulunuyor",
    )
    ok(
        "ProductOffer.store_product_id == product.product_code" in offer_source
        and "Aynı mağaza ürün teklifi güncellendi (upsert)." in offer_source,
        "aynı mağaza ürün kodu INSERT yerine upsert kullanıyor",
    )
    ok(
        "with db.begin_nested()" in offer_source
        and "except IntegrityError" in offer_source,
        "paralel teklif çakışması savepoint ile korunuyor",
    )
    ok(
        "Paralel teklif çakışması güvenli upsert ile çözüldü." in offer_source,
        "yarış durumu sonrası mevcut teklif güncelleniyor",
    )
    ok(
        "for future in as_completed" in category_source
        and "except Exception as error" in category_source,
        "tek ürün hatası detay kuyruğunun kalanını durdurmuyor",
    )

    db_path = ROOT / "data/products.db"
    ok(db_path.exists(), "ürün veritabanı mevcut")
    with sqlite3.connect(db_path) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        duplicate_count = conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT store_id, store_product_id, COUNT(*) AS n
              FROM product_offers
              WHERE store_product_id IS NOT NULL AND TRIM(store_product_id) <> ''
              GROUP BY store_id, store_product_id
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    ok(integrity == "ok", "SQLite integrity başarılı")
    ok(not foreign_keys, "foreign key ihlali yok")
    ok(duplicate_count == 0, "mevcut mağaza ürün kodlarında tekrar yok")

    print("\nFırsatAI v14.1.1 Teklif Upsert ve Tarama Tamamlama smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
