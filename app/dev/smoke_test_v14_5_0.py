from pathlib import Path
import sqlite3

from app.services.ai_comparison_v14_service import (
    analyze_global_product,
    data_quality_status,
)


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.5.0", "VERSION 14.5.0")

    con = sqlite3.connect(root / "data/products.db")
    con.row_factory = sqlite3.Row
    try:
        product = con.execute(
            """
            SELECT gp.id
            FROM global_products gp
            JOIN global_offers go ON go.global_product_id=gp.id
            WHERE gp.status='ACTIVE'
              AND go.is_active=1
              AND go.is_hidden=0
              AND go.current_price>0
            GROUP BY gp.id
            ORDER BY COUNT(go.id) DESC
            LIMIT 1
            """
        ).fetchone()
        ok(product is not None, "analiz edilebilir global ürün mevcut")
        result = analyze_global_product(product["id"])
        ok(result.get("available"), "global ürün akıllı analizi çalışıyor")
        ok(0 <= result["quality_score"] <= 100, "kalite puanı güvenli aralıkta")
        ok("market_summary" in result, "piyasa özeti üretiliyor")
        ok("warnings" in result, "şüpheli eşleşme uyarıları üretiliyor")
        ok("advantages" in result, "ürün avantaj özeti üretiliyor")

        status = data_quality_status(limit=50)
        ok(status["status"] == "AI_COMPARISON_READY", "veri kalitesi durumu hazır")
        ok(status["scanned_products"] > 0, "global ürünler toplu denetleniyor")
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

    route_text = (
        root / "app/web/global_marketplace_v14_routes.py"
    ).read_text(encoding="utf-8")
    template_text = (
        root / "app/templates/global_marketplace_product_v14.html"
    ).read_text(encoding="utf-8")
    main_text = (root / "main.py").read_text(encoding="utf-8")

    ok("analyze_global_product" in route_text, "ürün detayı akıllı analize bağlı")
    ok("ai-panel" in template_text, "akıllı karşılaştırma paneli arayüzde mevcut")
    ok("ai_comparison_v14_router" in main_text, "AI kalite router uygulamaya bağlı")

    print(
        "\nFırsatAI v14.5.0 AI Destekli Akıllı Karşılaştırma "
        "ve Veri Kalitesi smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
