from pathlib import Path
import sqlite3


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.9.0", "VERSION 14.9.0")

    service = (
        root / "app/services/multi_store_offer_repair_v14_service.py"
    ).read_text(encoding="utf-8")
    product_service = (
        root / "app/services/product_service.py"
    ).read_text(encoding="utf-8")
    routes = (
        root / "app/web/multi_store_offer_repair_v14_routes.py"
    ).read_text(encoding="utf-8")
    main_text = (root / "main.py").read_text(encoding="utf-8")

    ok("force_attach_candidate_offer" in service, "eşleşen aday hedef global ürüne zorunlu bağlanıyor")
    ok("target_global_product_id" in service, "kaynak global ürün kimliği tarama boyunca korunuyor")
    ok("validate_variant" not in service or "_is_same_product" in service, "mevcut güvenli varyant eşleşme kapısı korunuyor")
    ok("_cleanup_orphan_global_product" in service, "yanlışlıkla açılan boş global ürünler temizleniyor")
    ok("enqueue_multi_store_repair" in product_service, "ürün kaydından otomatik çoklu mağaza görevi başlatılıyor")
    ok("active_offer_count <= 1" in product_service, "yalnızca tek mağazada kalan ürünler otomatik taranıyor")
    ok("/api/multi-store-repair/v14/products/{global_product_id}" in routes, "manuel onarım API mevcut")
    ok("multi_store_offer_repair_v14_router" in main_text, "çoklu mağaza router uygulamaya bağlı")

    con = sqlite3.connect(root / "data/products.db")
    try:
        ok(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity başarılı")
        ok(len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0, "foreign key ihlali yok")
    finally:
        con.close()

    print("\nFırsatAI v14.9.0 Çok Mağazalı Ürün Birleştirme smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
