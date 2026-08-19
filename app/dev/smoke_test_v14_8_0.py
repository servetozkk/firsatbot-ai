from pathlib import Path
import sqlite3

from app.services.global_price_experience_v14_service import get_price_history


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.8.0", "VERSION 14.8.0")

    db_path = root / "data/products.db"
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            """
            SELECT global_product_id
            FROM global_offers
            WHERE is_active=1
              AND current_price>0
            LIMIT 1
            """
        ).fetchone()

        ok(row is not None, "fiyatlı global ürün mevcut")

        history = get_price_history(row[0], 90)
        ok(
            "summary" in history and "points" in history,
            "fiyat geçmişi özeti üretiliyor",
        )

        template_text = (
            root / "app/templates/global_marketplace_product_v14.html"
        ).read_text(encoding="utf-8")
        ok(
            "priceHistoryChart" in template_text,
            "fiyat grafiği arayüzde mevcut",
        )
        ok(
            "globalFavoriteBtn" in template_text,
            "global favori düğmesi mevcut",
        )
        ok(
            "Fiyat alarmı kur" in template_text,
            "fiyat alarmı düğmesi mevcut",
        )

        route_text = (
            root / "app/web/global_marketplace_v14_routes.py"
        ).read_text(encoding="utf-8")
        ok(
            "price-history" in route_text,
            "fiyat geçmişi API mevcut",
        )

        ok(
            con.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "SQLite integrity başarılı",
        )
        ok(
            len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0,
            "foreign key ihlali yok",
        )
    finally:
        con.close()

    print(
        "\nFırsatAI v14.8.0 Fiyat Geçmişi ve "
        "Gerçek Akakçe Deneyimi smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
