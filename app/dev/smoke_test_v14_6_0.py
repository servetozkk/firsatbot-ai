from pathlib import Path
import sqlite3

from app.services.live_price_refresh_v14_service import (
    get_live_price_status,
    list_refreshable_offers,
    live_price_summary,
)


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.6.0", "VERSION 14.6.0")

    summary = live_price_summary()
    ok(
        summary["status"] == "LIVE_PRICE_ENGINE_READY",
        "canlı fiyat motoru hazır",
    )
    ok(
        isinstance(summary["active_offer_count"], int),
        "aktif teklif sayısı hesaplanıyor",
    )
    ok(
        isinstance(list_refreshable_offers(limit=5), list),
        "yenilenebilir teklif kuyruğu oluşturuluyor",
    )
    ok(
        get_live_price_status()["status"] == "IDLE",
        "başlangıç görev durumu güvenli",
    )

    service_text = (
        root / "app/services/live_price_refresh_v14_service.py"
    ).read_text(encoding="utf-8")
    route_text = (
        root / "app/web/live_price_refresh_v14_routes.py"
    ).read_text(encoding="utf-8")
    template_text = (
        root / "app/templates/admin_live_prices_v14.html"
    ).read_text(encoding="utf-8")
    main_text = (root / "main.py").read_text(encoding="utf-8")

    ok("record_global_offer_price" in service_text, "fiyat geçmişi motoruna bağlı")
    ok("ThreadPoolExecutor" in service_text, "paralel teklif kontrolü mevcut")
    ok("retry_count" in service_text, "retry sistemi mevcut")
    ok("price_changed or stock_changed" in service_text, "delta güncelleme mevcut")
    ok("/api/live-prices/v14/refresh" in route_text, "toplu yenileme API mevcut")
    ok("progress_percent" in template_text, "canlı ilerleme paneli mevcut")
    ok("live_price_refresh_v14_router" in main_text, "canlı fiyat router uygulamaya bağlı")

    con = sqlite3.connect(root / "data/products.db")
    try:
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

    print("\nFırsatAI v14.6.0 Canlı Fiyat Güncelleme Motoru smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
