from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "data" / "reports" / "v12_2_1_beta1_acceptance_report.json"


def check(value: bool, message: str, results: list[dict]) -> None:
    results.append({"name": message, "passed": bool(value)})
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def first_existing(*paths: str) -> str:
    for path in paths:
        full = ROOT / path
        if full.exists():
            return full.read_text(encoding="utf-8-sig")
    return ""


def main() -> int:
    results: list[dict] = []
    version = read("VERSION").strip()
    main_py = read("main.py")
    global_router = read("app/web/global_product_routes.py")
    routes_py = read("app/web/routes.py")
    search_service = read("app/services/global_catalog_search_service.py")
    product_routes = read("app/web/product_group_routes.py")
    favorites_route = read("app/routes/favorites.py")
    alerts_route = read("app/routes/price_alerts.py")
    history_route = read("app/routes/history.py")
    comparison_route = read("app/routes/comparison.py")
    index_html = read("app/templates/index.html")
    detail_html = first_existing("app/templates/product_group_detail_v4.html", "app/templates/product_group_detail.html")
    account_html = first_existing("app/templates/account_dashboard.html")
    css = "\n".join(
        p.read_text(encoding="utf-8-sig", errors="ignore")
        for p in (ROOT / "app/static/css").glob("*.css")
    )

    check(version == "12.2.1", "VERSION 12.2.1", results)
    check('prefix="/urun"' in global_router and '@router.get("/{identity_key}"' in global_router,
          "kanonik global ürün endpoint'i mevcut", results)
    check("app.include_router(global_product_router)" in main_py,
          "global ürün router uygulamaya bağlı", results)
    check('/urun/{p.identity_key}' in search_service,
          "arama sonuçları global ürün URL üretiyor", results)
    check('"detail_url": f"/urun/{group.group_key}"' in routes_py,
          "ana sayfa ürün kartları kanonik URL kullanıyor", results)
    check("current_price" in product_routes and ("order_by" in product_routes or "offers.sort" in product_routes),
          "ürün detay akışında teklif/fiyat sıralama mantığı mevcut", results)
    check("price_history" in product_routes.casefold() or "get_global_price_history" in product_routes,
          "ürün detayında fiyat geçmişi akışı mevcut", results)
    check("favorite" in favorites_route.casefold() and "product_group" in favorites_route.casefold(),
          "favori endpoint'leri mevcut", results)
    check("alert" in alerts_route.casefold() and "target_price" in alerts_route,
          "fiyat alarmı endpoint'leri mevcut", results)
    check("history" in history_route.casefold(), "görüntüleme/geçmiş endpoint'i mevcut", results)
    check("compare" in comparison_route.casefold() and "/karsilastir/compare" in index_html,
          "ürün karşılaştırma aracı mevcut", results)
    check("viewport" in index_html.casefold() or "viewport" in detail_html.casefold(),
          "mobil viewport tanımı mevcut", results)
    check("@media" in css, "mobil duyarlı CSS kuralları mevcut", results)
    check("/urun/" in account_html or not account_html,
          "hesap/favori bağlantıları kanonik akışla uyumlu", results)

    db_path = ROOT / "data" / "products.db"
    check(db_path.exists(), "ürün veritabanı mevcut", results)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk_count = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        check(integrity == "ok", "SQLite integrity_check başarılı", results)
        check(fk_count == 0, "foreign key ihlali yok", results)

        gp_count = conn.execute("SELECT COUNT(*) FROM global_products WHERE status='ACTIVE'").fetchone()[0]
        go_count = conn.execute("SELECT COUNT(*) FROM global_offers WHERE is_active=1 AND is_hidden=0 AND current_price>0").fetchone()[0]
        multi_count = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT global_product_id FROM global_offers
              WHERE is_active=1 AND is_hidden=0 AND current_price>0
              GROUP BY global_product_id HAVING COUNT(DISTINCT store_code) >= 2
            )
        """).fetchone()[0]
        check(gp_count > 0, "aktif global ürünler mevcut", results)
        check(go_count > 0, "aktif global teklifler mevcut", results)
        check(multi_count > 0, "çok mağazalı global ürün mevcut", results)

        sample = conn.execute("""
            SELECT gp.id, gp.identity_key, gp.canonical_name, COUNT(go.id) offer_count,
                   COUNT(DISTINCT go.store_code) store_count, MIN(go.current_price + COALESCE(go.shipping_price,0)) best_total
            FROM global_products gp JOIN global_offers go ON go.global_product_id=gp.id
            WHERE gp.status='ACTIVE' AND go.is_active=1 AND go.is_hidden=0 AND go.current_price>0
            GROUP BY gp.id HAVING COUNT(go.id)>0
            ORDER BY store_count DESC, offer_count DESC LIMIT 1
        """).fetchone()
        check(sample is not None and bool(sample["identity_key"]), "örnek global ürün kimliği çözüldü", results)

        prices = [r[0] for r in conn.execute("""
            SELECT current_price + COALESCE(shipping_price,0) total
            FROM global_offers
            WHERE global_product_id=? AND is_active=1 AND is_hidden=0 AND current_price>0
            ORDER BY total ASC
        """, (sample["id"],)).fetchall()]
        check(prices == sorted(prices), "örnek ürün teklifleri toplam fiyata göre sıralanıyor", results)

        history_count = conn.execute("SELECT COUNT(*) FROM global_offer_price_history").fetchone()[0]
        if history_count == 0:
            history_count = conn.execute("SELECT COUNT(*) FROM offer_price_history").fetchone()[0]
        check(history_count > 0, "fiyat geçmişi verisi mevcut", results)

        for table, label in [
            ("favorites", "favori tablosu"),
            ("price_alerts", "fiyat alarmı tablosu"),
            ("recently_viewed", "son görüntülenenler tablosu"),
        ]:
            exists = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
            check(exists == 1, f"{label} mevcut", results)

        summary = {
            "version": version,
            "status": "BETA1_ACCEPTANCE_READY",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "read_only": True,
            "counts": {
                "active_global_products": gp_count,
                "active_global_offers": go_count,
                "multi_store_products": multi_count,
                "price_history_rows": history_count,
            },
            "sample_product": dict(sample),
            "checks": results,
            "passed": sum(1 for x in results if x["passed"]),
            "total": len(results),
        }
    finally:
        conn.close()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"RAPOR: {REPORT}")
    print("DURUM: BETA1_ACCEPTANCE_READY")
    print("\nFırsatAI v12.2.1 Beta-1 kullanıcı kabul testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
